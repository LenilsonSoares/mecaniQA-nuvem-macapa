"""Exporta do Prometheus a série horária de requisições com sucesso e com erro (OAT 4).

Cada linha do CSV representa uma hora cheia, rotulada pelo seu INÍCIO: a linha
"10:00" conta as requisições entre 10:00 e 11:00 (``increase`` do contador em 1 h).
Horas em que o Prometheus raspou a API menos de 90% do tempo (máquina parada,
queda de energia) saem vazias, para não parecerem horas de pouco tráfego.

Uso (com a pilha da pasta app-monitoring rodando):
    py coletar_prometheus.py                 # últimas 96 h até a última hora cheia
    py coletar_prometheus.py --horas 120     # 5 dias
    py coletar_prometheus.py --fim 2026-12-01T08:00

Só usa a biblioteca padrão do Python, para rodar em qualquer máquina da equipe.
"""

import argparse
import csv
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Horário de Brasília/Bahia (UTC-3, sem horário de verão). Usamos offset fixo porque
# o módulo zoneinfo no Windows depende de um pacote extra (tzdata).
FUSO_LOCAL = timezone(timedelta(hours=-3), "UTC-03")

CONSULTAS = {
    "sucesso": "sum(increase(mecaniqa_api_requests_success_total[1h]))",
    "erro": "sum(increase(mecaniqa_api_requests_error_total[1h]))",
}

# Raspagem a cada 5 s → 720 amostras por hora; abaixo de 90% a hora é considerada sem dado.
# up vale 1 (API respondeu) ou 0 (caiu): sum_over_time conta só as raspagens com a API no ar.
AMOSTRAS_POR_HORA = 3600 // 5
COBERTURA_MINIMA = 0.9
CONSULTA_COBERTURA = 'sum_over_time(up{job="mecaniqa-django-api"}[1h])'

PASTA_OAT4 = Path(__file__).resolve().parents[1]
SAIDA_PADRAO = PASTA_OAT4 / "dados" / "serie_horaria.csv"


def ultima_hora_cheia(agora: datetime) -> datetime:
    """Arredonda para baixo até a hora cheia, para cada ponto cobrir uma hora completa."""
    return agora.replace(minute=0, second=0, microsecond=0)


def consultar_intervalo(prometheus: str, promql: str, inicio: datetime, fim: datetime) -> dict[int, float]:
    """Executa /api/v1/query_range com passo de 1 h e devolve {timestamp_unix: valor}."""
    parametros = urllib.parse.urlencode({
        "query": promql,
        "start": int(inicio.timestamp()),
        "end": int(fim.timestamp()),
        "step": "3600",
    })
    url = f"{prometheus.rstrip('/')}/api/v1/query_range?{parametros}"
    with urllib.request.urlopen(url, timeout=30) as resposta:
        corpo = json.loads(resposta.read().decode("utf-8"))
    if corpo.get("status") != "success":
        raise RuntimeError(f"Prometheus respondeu com erro: {corpo}")
    resultado = corpo["data"]["result"]
    if not resultado:
        return {}
    return {int(float(ts)): float(valor) for ts, valor in resultado[0]["values"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--prometheus", default="http://localhost:9090", help="URL do Prometheus")
    parser.add_argument("--horas", type=int, default=96,
                        help="horas exportadas (padrão 96 = 1 dia de aquecimento + 72 h avaliadas)")
    parser.add_argument("--fim", help="última hora (horário local, ex.: 2026-12-01T08:00); padrão: agora")
    parser.add_argument("--saida", type=Path, default=SAIDA_PADRAO, help="arquivo CSV de saída")
    args = parser.parse_args()

    if args.fim:
        fim = datetime.fromisoformat(args.fim).replace(tzinfo=FUSO_LOCAL)
    else:
        fim = datetime.now(FUSO_LOCAL)
    fim = ultima_hora_cheia(fim)
    # start e end são inclusivos no query_range: (horas - 1) passos geram exatamente `horas` pontos.
    inicio = fim - timedelta(hours=args.horas - 1)

    series = {nome: consultar_intervalo(args.prometheus, q, inicio, fim) for nome, q in CONSULTAS.items()}
    cobertura = consultar_intervalo(args.prometheus, CONSULTA_COBERTURA, inicio, fim)

    linhas, faltantes = [], []
    instante = inicio
    while instante <= fim:
        ts = int(instante.timestamp())
        valores = {nome: series[nome].get(ts) for nome in CONSULTAS}
        # O ponto em T resume a hora (T-1h, T]: rotulamos pelo início dessa hora.
        inicio_da_hora = instante - timedelta(hours=1)
        if cobertura.get(ts, 0) < COBERTURA_MINIMA * AMOSTRAS_POR_HORA:
            valores = {nome: None for nome in CONSULTAS}
        if any(v is None for v in valores.values()):
            faltantes.append(inicio_da_hora)
        linhas.append({
            "timestamp": inicio_da_hora.astimezone(FUSO_LOCAL).strftime("%Y-%m-%d %H:%M"),
            # increase() extrapola e pode gerar decimais; arredondamos para contagem inteira.
            **{nome: ("" if v is None else round(v)) for nome, v in valores.items()},
        })
        instante += timedelta(hours=1)

    args.saida.parent.mkdir(parents=True, exist_ok=True)
    with args.saida.open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=["timestamp", *CONSULTAS])
        escritor.writeheader()
        escritor.writerows(linhas)

    print(f"Período coberto: {inicio - timedelta(hours=1):%d/%m/%Y %H:%M} até {fim:%d/%m/%Y %H:%M} (UTC-3)")
    print(f"Horas exportadas: {len(linhas)} | arquivo: {args.saida}")
    if faltantes:
        print(f"ATENÇÃO: {len(faltantes)} hora(s) sem dado (coleta parada?). Primeira: {faltantes[0]:%d/%m %H:%M}.")
        print("Registre esses horários na apresentação e explique o tratamento.")
    if any(linhas[0][nome] == "" for nome in CONSULTAS):
        print(f"ERRO: a primeira hora ({linhas[0]['timestamp']}) está incompleta: a coleta começou no meio dela "
              "ou ainda não tinha começado.")
        print("Rode de novo depois da próxima hora cheia (ou ajuste --fim/--horas) para ter todas as horas completas.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
