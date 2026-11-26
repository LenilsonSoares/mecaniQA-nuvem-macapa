"""Motor preditivo da OAT 4: 7 baselines, 4 partições (MAE/MSE) e Random Forest.

Lê a série horária exportada por ``coleta/coletar_prometheus.py`` e gera, em
``oat4/resultados/``, todas as tabelas e gráficos usados nos slides:

* 7 baselines por série (sucesso e erro): lags de 1, 3, 12 e 24 h e
  médias móveis simples de 3, 12 e 24 h;
* avaliação nas 4 partições cumulativas das últimas 72 h (18, 36, 54 e 72 h);
* Random Forest com feature engineering temporal, avaliado nas mesmas horas.

Protocolo (sem vazamento de informação do futuro):
* As primeiras horas antes da janela de 72 h servem só de histórico,
  para que o lag de 24 h já tenha valor desde a primeira hora avaliada.
* Toda previsão da hora ``t`` usa somente horas anteriores a ``t``.
* O Random Forest é avaliado em "walk-forward": para cada hora ``t`` da janela,
  é treinado com as horas anteriores a ``t`` e prevê ``t``.

Uso:
    py analise_oat4.py                       # usa dados/serie_horaria.csv
    py analise_oat4.py --dados outro.csv --refit-a-cada 3
"""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # gera arquivos PNG sem abrir janela
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

PASTA_OAT4 = Path(__file__).resolve().parents[1]
SERIES = {"sucesso": "Requisições com sucesso (2xx)", "erro": "Requisições com erro (4xx/5xx)"}
JANELA_HORAS = 72
PARTICOES = {"P1 (18 h)": 18, "P2 (36 h)": 36, "P3 (54 h)": 54, "P4 (72 h)": 72}
LAGS_BASELINE = (1, 3, 12, 24)
MEDIAS_BASELINE = (3, 12, 24)
NOME_RF = "Random Forest"


# --------------------------------------------------------------------------- dados
def carregar_serie(caminho: Path) -> pd.DataFrame:
    """Lê o CSV horário, valida a frequência e trata horas faltantes."""
    dados = pd.read_csv(caminho, parse_dates=["timestamp"]).set_index("timestamp").sort_index()
    faltando_colunas = set(SERIES) - set(dados.columns)
    if faltando_colunas:
        raise ValueError(f"Colunas ausentes no CSV: {sorted(faltando_colunas)}")
    if dados.index.has_duplicates:
        raise ValueError("Há horas duplicadas no CSV.")
    # Reindexa hora a hora: buracos de coleta (queda de energia) viram NaN explícitos.
    completo = pd.date_range(dados.index.min(), dados.index.max(), freq="h")
    dados = dados.reindex(completo).rename_axis("timestamp")
    faltantes = int(dados[list(SERIES)].isna().any(axis=1).sum())
    if faltantes:
        print(f"Aviso: {faltantes} hora(s) sem dado; preenchidas por interpolação linear no tempo.")
        dados[list(SERIES)] = dados[list(SERIES)].interpolate(method="time", limit_direction="both")
    if len(dados) < JANELA_HORAS + 24:
        raise ValueError(
            f"São necessárias pelo menos {JANELA_HORAS + 24} horas (24 de histórico + 72 avaliadas); "
            f"o arquivo tem {len(dados)}."
        )
    return dados.astype(float)


# ---------------------------------------------------------------------- baselines
def prever_baselines(y: pd.Series) -> pd.DataFrame:
    """Calcula os 7 baselines; ``shift(1)`` garante que a hora prevista não entra na média."""
    previsoes = {f"Lag {k} h": y.shift(k) for k in LAGS_BASELINE}
    previsoes.update({f"Média móvel {m} h": y.shift(1).rolling(m).mean() for m in MEDIAS_BASELINE})
    return pd.DataFrame(previsoes)


# ------------------------------------------------------------- feature engineering
def periodo_do_dia(hora: int) -> int:
    """0 = madrugada (0-5 h), 1 = manhã (6-11 h), 2 = tarde (12-17 h), 3 = noite (18-23 h)."""
    return hora // 6


def criar_features(dados: pd.DataFrame, alvo: str) -> pd.DataFrame:
    """Atributos da hora ``t`` construídos apenas com informação disponível antes de ``t``."""
    y = dados[alvo]
    outra = dados[[c for c in SERIES if c != alvo][0]]
    passado = y.shift(1)
    feats = pd.DataFrame(index=dados.index)
    # Calendário: o gerador do professor segue um padrão diário (picos ~10 h e ~15 h).
    feats["hora_do_dia"] = dados.index.hour
    feats["periodo_do_dia"] = feats["hora_do_dia"].map(periodo_do_dia)
    feats["dia_da_semana"] = dados.index.dayofweek
    # Memória recente e sazonalidade diária (lag 24 h compara a mesma hora de ontem).
    for k in (1, 2, 3, 24):
        feats[f"lag_{k}h"] = y.shift(k)
    # Nível e volatilidade recentes em janelas deslizantes.
    for m in (3, 6, 12, 24):
        feats[f"media_movel_{m}h"] = passado.rolling(m).mean()
        feats[f"desvio_movel_{m}h"] = passado.rolling(m).std()
    # Tendência entre horas consecutivas e influência cruzada da outra série.
    feats["tendencia_1h"] = y.shift(1) - y.shift(2)
    feats[f"{[c for c in SERIES if c != alvo][0]}_lag_1h"] = outra.shift(1)
    return feats


def prever_random_forest(dados: pd.DataFrame, alvo: str, inicio_janela: int, refit_a_cada: int, semente: int):
    """Walk-forward: para cada hora da janela, treina com as horas anteriores e prevê a hora."""
    feats = criar_features(dados, alvo)
    y = dados[alvo]
    previsoes = pd.Series(np.nan, index=dados.index, name=NOME_RF)
    modelo = None
    for posicao in range(inicio_janela, len(dados)):
        if modelo is None or (posicao - inicio_janela) % refit_a_cada == 0:
            # A partir do scikit-learn 1.4, o Random Forest aceita NaN nas features
            # (horas iniciais sem lag 24 h), então não descartamos o começo do histórico.
            treino = slice(1, posicao)
            modelo = RandomForestRegressor(
                n_estimators=300, min_samples_leaf=2, random_state=semente, n_jobs=-1
            ).fit(feats.iloc[treino], y.iloc[treino])
        previsoes.iloc[posicao] = modelo.predict(feats.iloc[[posicao]])[0]
    importancias = pd.Series(modelo.feature_importances_, index=feats.columns).sort_values(ascending=False)
    return previsoes, importancias


# ------------------------------------------------------------------------ métricas
def avaliar_particoes(real: pd.Series, previsoes: pd.DataFrame, inicio_janela: int) -> pd.DataFrame:
    """MAE e MSE de cada modelo em cada partição cumulativa da janela de 72 h."""
    linhas = []
    for nome_particao, horas in PARTICOES.items():
        fatia = slice(inicio_janela, inicio_janela + horas)
        y = real.iloc[fatia]
        for modelo in previsoes.columns:
            p = previsoes[modelo].iloc[fatia]
            linhas.append({
                "particao": nome_particao,
                "modelo": modelo,
                "MAE": mean_absolute_error(y, p),
                "MSE": mean_squared_error(y, p),
            })
    return pd.DataFrame(linhas)


# ------------------------------------------------------------------------ gráficos
def grafico_serie(dados: pd.DataFrame, inicio_janela: int, pasta: Path) -> None:
    fig, eixos = plt.subplots(2, 1, figsize=(13, 7), sharex=True)
    for eixo, (coluna, titulo) in zip(eixos, SERIES.items()):
        eixo.plot(dados.index, dados[coluna], color="black", linewidth=1.4)
        eixo.axvspan(dados.index[0], dados.index[inicio_janela - 1], color="grey", alpha=0.15,
                     label="histórico (aquecimento)")
        eixo.set_title(titulo)
        eixo.set_ylabel("requisições/hora")
        eixo.grid(alpha=0.25)
        eixo.legend(loc="upper left")
    fig.suptitle("Série horária coletada do Prometheus")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(pasta / "01_serie_coletada.png", dpi=160)
    plt.close(fig)


def grafico_heatmap(tabela: pd.DataFrame, metrica: str, serie: str, pasta: Path) -> None:
    matriz = tabela.pivot(index="modelo", columns="particao", values=metrica)[list(PARTICOES)]
    matriz = matriz.loc[matriz[list(PARTICOES)[-1]].sort_values().index]
    fig, eixo = plt.subplots(figsize=(8, 5))
    imagem = eixo.imshow(matriz.values, cmap="RdYlGn_r", aspect="auto")
    eixo.set_xticks(range(len(matriz.columns)), matriz.columns)
    eixo.set_yticks(range(len(matriz.index)), matriz.index)
    for i in range(matriz.shape[0]):
        for j in range(matriz.shape[1]):
            eixo.text(j, i, f"{matriz.values[i, j]:.1f}", ha="center", va="center", fontsize=9)
    eixo.set_title(f"{metrica} por modelo e partição — {SERIES[serie]}\n(menor é melhor)")
    fig.colorbar(imagem, ax=eixo, shrink=0.8)
    fig.tight_layout()
    fig.savefig(pasta / f"02_heatmap_{metrica.lower()}_{serie}.png", dpi=160)
    plt.close(fig)


def grafico_previsoes(real: pd.Series, previsoes: pd.DataFrame, tabela: pd.DataFrame,
                      inicio_janela: int, serie: str, pasta: Path) -> None:
    final = tabela[tabela["particao"] == list(PARTICOES)[-1]]
    melhor_baseline = final[final["modelo"] != NOME_RF].sort_values("MAE")["modelo"].iloc[0]
    janela = slice(inicio_janela, None)
    fig, eixo = plt.subplots(figsize=(13, 5))
    eixo.plot(real.index[janela], real.iloc[janela], color="black", linewidth=2, label="Real")
    eixo.plot(real.index[janela], previsoes[melhor_baseline].iloc[janela], "--", label=f"Melhor baseline: {melhor_baseline}")
    eixo.plot(real.index[janela], previsoes[NOME_RF].iloc[janela], label=NOME_RF)
    for horas in list(PARTICOES.values())[:-1]:
        eixo.axvline(real.index[inicio_janela + horas], color="grey", linestyle=":", linewidth=1)
    eixo.set_title(f"{SERIES[serie]} — real × previsões nas 72 h avaliadas (linhas pontilhadas = partições)")
    eixo.set_ylabel("requisições/hora")
    eixo.legend()
    eixo.grid(alpha=0.25)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(pasta / f"03_previsoes_{serie}.png", dpi=160)
    plt.close(fig)


def grafico_evolucao(tabela: pd.DataFrame, serie: str, pasta: Path) -> None:
    fig, eixo = plt.subplots(figsize=(9, 5))
    for modelo, grupo in tabela.groupby("modelo", sort=False):
        estilo = dict(linewidth=3, color="black") if modelo == NOME_RF else dict(linewidth=1.2, alpha=0.8)
        eixo.plot(grupo["particao"], grupo["MAE"], marker="o", label=modelo, **estilo)
    eixo.set_title(f"Evolução do MAE conforme cresce o histórico — {SERIES[serie]}")
    eixo.set_ylabel("MAE (requisições/hora)")
    eixo.legend(fontsize=8, ncol=2)
    eixo.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(pasta / f"04_evolucao_mae_{serie}.png", dpi=160)
    plt.close(fig)


def grafico_importancias(importancias: pd.Series, serie: str, pasta: Path) -> None:
    top = importancias.head(10).iloc[::-1]
    fig, eixo = plt.subplots(figsize=(8, 5))
    eixo.barh(top.index, top.values)
    eixo.set_title(f"Features mais importantes do Random Forest — {SERIES[serie]}")
    eixo.set_xlabel("importância (redução de impureza)")
    fig.tight_layout()
    fig.savefig(pasta / f"05_importancia_features_{serie}.png", dpi=160)
    plt.close(fig)


# ---------------------------------------------------------------------------- main
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dados", type=Path, default=PASTA_OAT4 / "dados" / "serie_horaria.csv")
    parser.add_argument("--saida", type=Path, default=PASTA_OAT4 / "resultados")
    parser.add_argument("--refit-a-cada", type=int, default=1,
                        help="re-treina o Random Forest a cada N horas (1 = toda hora)")
    parser.add_argument("--semente", type=int, default=42)
    args = parser.parse_args()

    dados = carregar_serie(args.dados)
    # A janela avaliada são sempre as ÚLTIMAS 72 h; o que vem antes é histórico.
    inicio_janela = len(dados) - JANELA_HORAS
    args.saida.mkdir(parents=True, exist_ok=True)
    print(f"Série: {dados.index[0]:%d/%m %H:%M} → {dados.index[-1]:%d/%m %H:%M} ({len(dados)} h); "
          f"janela avaliada a partir de {dados.index[inicio_janela]:%d/%m %H:%M}")
    grafico_serie(dados, inicio_janela, args.saida)

    todas = []
    for serie in SERIES:
        previsoes = prever_baselines(dados[serie])
        previsoes[NOME_RF], importancias = prever_random_forest(
            dados, serie, inicio_janela, args.refit_a_cada, args.semente
        )
        tabela = avaliar_particoes(dados[serie], previsoes, inicio_janela)
        tabela.insert(0, "serie", serie)
        todas.append(tabela)

        for metrica in ("MAE", "MSE"):
            pivo = tabela.pivot(index="modelo", columns="particao", values=metrica)[list(PARTICOES)]
            pivo.round(2).to_csv(args.saida / f"tabela_{metrica.lower()}_{serie}.csv", encoding="utf-8-sig")
            grafico_heatmap(tabela, metrica, serie, args.saida)
        grafico_previsoes(dados[serie], previsoes, tabela, inicio_janela, serie, args.saida)
        grafico_evolucao(tabela, serie, args.saida)
        grafico_importancias(importancias, serie, args.saida)
        importancias.round(4).to_csv(args.saida / f"importancia_features_{serie}.csv", encoding="utf-8-sig")
        previsoes.iloc[inicio_janela:].assign(real=dados[serie].iloc[inicio_janela:]).round(2).to_csv(
            args.saida / f"previsoes_{serie}.csv", encoding="utf-8-sig"
        )

        final = tabela[tabela["particao"] == list(PARTICOES)[-1]].sort_values("MAE")
        print(f"\n=== {SERIES[serie]} — partição P4 (72 h), ordenado por MAE ===")
        print(final[["modelo", "MAE", "MSE"]].round(2).to_string(index=False))

    pd.concat(todas).round(4).to_csv(args.saida / "metricas_todas.csv", index=False, encoding="utf-8-sig")
    print(f"\nTabelas e gráficos salvos em: {args.saida}")


if __name__ == "__main__":
    main()
