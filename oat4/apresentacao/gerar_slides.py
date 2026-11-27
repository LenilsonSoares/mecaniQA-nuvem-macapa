"""Gera a apresentação da OAT 4 no modelo da disciplina (mecaniQA_oat4_macapa.pptx).

Usa como base o .pptx da OAT 2 de Nuvem (docs/apresentacoes/mecaniQA_oat2_macapa.pptx),
que segue o Modelo de Apresentação da UNEX: capa, agenda, logo, rodapé e numeração.

* Antes da coleta: gera o roteiro completo com espaços marcados para gráficos e números.
* Depois de rodar coleta/ e analise/: insere automaticamente os gráficos de
  oat4/resultados/, as tabelas de MAE/MSE e os números (período, horas, melhor modelo).
* Prints do Grafana: salve em oat4/apresentacao/prints/ (veja o LEIA-ME de lá)
  e rode de novo; aceita .png ou .jpg.

Uso (na pasta oat4):
    py apresentacao/gerar_slides.py          # gera o .pptx
    py apresentacao/gerar_slides.py --pdf    # gera o .pptx e exporta o PDF (PowerPoint no Windows)
Depois, abra o .pptx no Google Slides (fonte Poppins do modelo) e exporte o PDF.
"""

import argparse
import copy
import subprocess
import sys
from pathlib import Path

import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.util import Inches, Pt

PASTA_OAT4 = Path(__file__).resolve().parents[1]
RAIZ = PASTA_OAT4.parent
MODELO = RAIZ / "docs" / "apresentacoes" / "mecaniQA_oat2_macapa.pptx"
RESULTADOS = PASTA_OAT4 / "resultados"
PRINTS = PASTA_OAT4 / "apresentacao" / "prints"
DADOS = PASTA_OAT4 / "dados" / "serie_horaria.csv"
SAIDA = PASTA_OAT4 / "apresentacao" / "mecaniQA_oat4_macapa.pptx"

# Identidade visual do modelo (extraída do .pptx da OAT 2).
FONTE = "Poppins"
PRETO = RGBColor(0x00, 0x00, 0x00)
VERDE = RGBColor(0x4E, 0x7A, 0x27)
VERDE_CLARO = RGBColor(0xE9, 0xF1, 0xE1)
CINZA_CARD = RGBColor(0xF3, 0xF3, 0xF3)
CINZA_TEXTO = RGBColor(0x80, 0x80, 0x80)
CINZA_BORDA = RGBColor(0xB0, 0xB0, 0xB0)
ESCURO = RGBColor(0x1F, 0x1F, 0x1F)
BRANCO = RGBColor(0xFF, 0xFF, 0xFF)
RODAPE = "MecâniQA | OAT 4"

EQUIPE = ["Artur Maia Coqueiro", "Douglas Renan Santos", "Kayky Ribeiro Souza",
          "Lenilson Dias Soares", "Joab Nascimento Rodrigues"]


# ============================================================ utilidades do modelo
def clonar_slide(prs, origem):
    """Duplica um slide do modelo (logo, rodapé e numeração) no fim da apresentação."""
    novo = prs.slides.add_slide(origem.slide_layout)
    for ph in list(novo.placeholders):
        ph._element.getparent().remove(ph._element)
    for forma in origem.shapes:
        elemento = copy.deepcopy(forma._element)
        novo.shapes._spTree.insert_element_before(elemento, "p:extLst")
        # Imagens (logo) precisam de relacionamento próprio no slide novo.
        for blip in elemento.xpath(".//a:blip"):
            rid = blip.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
            parte = origem.part.related_part(rid)
            blip.set("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed",
                     novo.part.relate_to(parte, RT.IMAGE))
    return novo


def remover_slide(prs, slide):
    lista = prs.slides._sldIdLst
    for sld in list(lista):
        if prs.part.related_part(sld.rId) is slide.part:
            prs.part.drop_rel(sld.rId)
            lista.remove(sld)
            return


def limpar_conteudo(slide, manter_titulo=True):
    """Remove tudo que não é título, logo, rodapé ou número de página."""
    for forma in list(slide.shapes):
        texto = forma.text_frame.text if forma.has_text_frame else ""
        manter = (
            forma.shape_type == 13  # imagem (logo)
            or forma.is_placeholder  # número da página
            or texto.startswith("MecaniQA ·")  # rodapé
            or (manter_titulo and forma.has_text_frame and forma.top < Inches(0.6) and forma.left < Inches(1))
        )
        if not manter:
            forma._element.getparent().remove(forma._element)
        elif texto.startswith("MecaniQA ·"):
            definir_texto(forma.text_frame, RODAPE)


def definir_texto(quadro, texto):
    """Troca o texto preservando a formatação do primeiro trecho (run) do modelo."""
    p = quadro.paragraphs[0]
    if p.runs:
        p.runs[0].text = texto
        for r in p.runs[1:]:
            r._r.getparent().remove(r._r)
    else:
        p.text = texto
    for extra in quadro.paragraphs[1:]:
        extra._p.getparent().remove(extra._p)


def titulo(slide, texto):
    for forma in slide.shapes:
        if forma.has_text_frame and forma.top < Inches(0.6) and forma.left < Inches(1):
            definir_texto(forma.text_frame, texto)
            forma.width = Inches(7.1)
            forma.text_frame.word_wrap = True
            return


def caixa(slide, x, y, w, h, linhas, tamanho=12, cor=PRETO, negrito_primeira=False,
          alinhar=PP_ALIGN.LEFT, ancora=MSO_ANCHOR.TOP, nome=None, italico=False):
    """Caixa de texto; `linhas` pode ser str ou lista (cada item vira um parágrafo)."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if nome:
        tb.name = nome
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.vertical_anchor = ancora
    for i, linha in enumerate([linhas] if isinstance(linhas, str) else linhas):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = alinhar
        p.space_after = Pt(4)
        trechos = linha if isinstance(linha, list) else [(linha, negrito_primeira and i == 0)]
        for texto, negrito in trechos:
            r = p.add_run()
            r.text = texto
            r.font.name, r.font.size, r.font.bold = FONTE, Pt(tamanho), negrito
            r.font.color.rgb, r.font.italic = cor, italico
    return tb


def cartao(slide, x, y, w, h, titulo_txt, corpo, fundo=CINZA_CARD, cor_titulo=PRETO,
           cor_corpo=PRETO, tam_titulo=13, tam_corpo=11, numero=None):
    forma = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    forma.adjustments[0] = 0.06
    forma.fill.solid()
    forma.fill.fore_color.rgb = fundo
    forma.line.fill.background()
    forma.shadow.inherit = False
    deslocamento = 0
    if numero:
        caixa(slide, x + 0.15, y + 0.08, 0.6, 0.45, numero, tamanho=20, cor=VERDE, negrito_primeira=True)
        deslocamento = 0.42
    caixa(slide, x + 0.12, y + 0.1 + deslocamento, w - 0.24, 0.4, titulo_txt, tamanho=tam_titulo,
          cor=cor_titulo, negrito_primeira=True)
    caixa(slide, x + 0.12, y + 0.45 + deslocamento, w - 0.24, h - 0.55 - deslocamento, corpo,
          tamanho=tam_corpo, cor=cor_corpo)
    return forma


def seta(slide, x1, y1, x2, y2):
    linha = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    linha.line.color.rgb = CINZA_BORDA
    linha.line.width = Pt(1.75)
    linha.line._get_or_add_ln().append(_ponta_de_seta())
    return linha


def _ponta_de_seta():
    from lxml import etree
    return etree.fromstring('<a:tailEnd xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" type="triangle"/>')


def fonte(slide, texto):
    caixa(slide, 0.38, 4.7, 8.6, 0.3, texto, tamanho=10, cor=CINZA_TEXTO)


def destaque(slide, x, y, w, texto, tamanho=13):
    caixa(slide, x, y, w, 0.5, texto, tamanho=tamanho, cor=VERDE, negrito_primeira=True)


def localizar_imagem(arquivo):
    """Aceita o nome com .png ou com .jpg/.jpeg (prints tirados de jeitos diferentes)."""
    if not arquivo:
        return None
    base = Path(arquivo)
    for candidato in [base, *(base.with_suffix(ext) for ext in (".png", ".jpg", ".jpeg", ".PNG", ".JPG"))]:
        if candidato.is_file():
            return candidato
    return None


def imagem_ou_espaco(slide, arquivo, x, y, w, h, rotulo):
    """Insere a imagem ajustada à área; sem o arquivo, desenha um espaço reservado."""
    arquivo = localizar_imagem(arquivo)
    if arquivo:
        from PIL import Image
        with Image.open(arquivo) as im:
            proporcao = im.width / im.height
        largura, altura = (w, w / proporcao) if w / proporcao <= h else (h * proporcao, h)
        slide.shapes.add_picture(str(arquivo), Inches(x + (w - largura) / 2), Inches(y + (h - altura) / 2),
                                 Inches(largura), Inches(altura))
        return True
    forma = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    forma.fill.solid()
    forma.fill.fore_color.rgb = BRANCO
    forma.line.color.rgb = CINZA_BORDA
    forma.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    forma.shadow.inherit = False
    caixa(slide, x + 0.1, y, w - 0.2, h, ["⟶ INSERIR", rotulo], tamanho=10, cor=CINZA_TEXTO,
          alinhar=PP_ALIGN.CENTER, ancora=MSO_ANCHOR.MIDDLE, italico=True)
    return False


def tabela(slide, x, y, w, linhas, larguras, tamanho=10, destaque_linha=None, numeros_a_direita=False):
    n_lin, n_col = len(linhas), len(linhas[0])
    forma = slide.shapes.add_table(n_lin, n_col, Inches(x), Inches(y), Inches(w), Inches(0.3 * n_lin))
    tab = forma.table
    for j, larg in enumerate(larguras):
        tab.columns[j].width = Inches(larg)
    for i, linha in enumerate(linhas):
        tab.rows[i].height = Inches(0.3)
        for j, valor in enumerate(linha):
            celula = tab.cell(i, j)
            celula.margin_left = celula.margin_right = Inches(0.06)
            celula.margin_top = celula.margin_bottom = Inches(0.02)
            celula.vertical_anchor = MSO_ANCHOR.MIDDLE
            celula.fill.solid()
            celula.fill.fore_color.rgb = (ESCURO if i == 0 else VERDE_CLARO if i == destaque_linha
                                          else BRANCO if i % 2 else CINZA_CARD)
            p = celula.text_frame.paragraphs[0]
            numero = str(valor).replace(".", "").replace(",", "").replace("—", "").strip().isdigit()
            p.alignment = PP_ALIGN.RIGHT if (numero or (i == 0 and j > 0 and numeros_a_direita)) else PP_ALIGN.LEFT
            r = p.add_run()
            r.text = str(valor)
            r.font.name, r.font.size = FONTE, Pt(tamanho)
            r.font.bold = i == 0 or j == 0
            r.font.color.rgb = BRANCO if i == 0 else PRETO
    return forma


def notas(slide, texto):
    slide.notes_slide.notes_text_frame.text = texto


# =========================================================== dados da análise
def carregar_resumo():
    """Lê dados e métricas, se a coleta e a análise já tiverem sido executadas."""
    resumo = {"tem_dados": DADOS.is_file(), "tem_metricas": (RESULTADOS / "metricas_todas.csv").is_file()}
    if resumo["tem_dados"]:
        serie = pd.read_csv(DADOS, parse_dates=["timestamp"])
        janela = serie.tail(72)
        resumo.update(
            inicio=serie["timestamp"].min(), fim=serie["timestamp"].max(), horas=len(serie),
            faltantes=int(serie[["sucesso", "erro"]].isna().any(axis=1).sum()),
            inicio_janela=janela["timestamp"].min(),
            total_sucesso=int(janela["sucesso"].sum()), total_erro=int(janela["erro"].sum()),
        )
    if resumo["tem_metricas"]:
        m = pd.read_csv(RESULTADOS / "metricas_todas.csv")
        resumo["metricas"] = m
        for serie in ("sucesso", "erro"):
            dados = m[m["serie"] == serie]
            final = dados[dados["particao"] == "P4 (72 h)"].sort_values("MAE")
            base = final[final["modelo"] != "Random Forest"]
            rf = final[final["modelo"] == "Random Forest"].iloc[0]
            rf_p = dados[dados["modelo"] == "Random Forest"].set_index("particao")["MAE"]
            info = {
                "melhor_baseline": base.iloc[0]["modelo"], "mae_baseline": base.iloc[0]["MAE"],
                "mae_rf": rf["MAE"], "rf_venceu": rf["MAE"] < base.iloc[0]["MAE"],
                "pior_baseline": base.iloc[-1]["modelo"], "mae_pior": base.iloc[-1]["MAE"],
                "rf_p1": rf_p.get("P1 (18 h)"), "rf_p4": rf_p.get("P4 (72 h)"),
                "posicao_rf": 1 + list(final["modelo"]).index("Random Forest"),
            }
            arquivo_imp = RESULTADOS / f"importancia_features_{serie}.csv"
            if arquivo_imp.is_file():
                imp = pd.read_csv(arquivo_imp, index_col=0).iloc[:, 0]
                info["top_features"] = list(imp.index[:2])
                info["top_peso"] = float(imp.iloc[0])
            resumo[serie] = info
    return resumo


def num(valor, casas=1):
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def tabela_particoes(resumo, serie, metrica):
    """Linhas [modelo, P1, P2, P3, P4], na ordem do MAE em P4 (mesma ordem nas duas tabelas)."""
    m = resumo["metricas"]
    ordem = (m[(m["serie"] == serie) & (m["particao"] == "P4 (72 h)")].sort_values("MAE")["modelo"].tolist())
    pivo = m[m["serie"] == serie].pivot(index="modelo", columns="particao", values=metrica)
    pivo = pivo[["P1 (18 h)", "P2 (36 h)", "P3 (54 h)", "P4 (72 h)"]].loc[ordem]

    def formatar(v):
        # MSE tem valores grandes: em milhares (k) para caber e ser lido de longe.
        return num(v) if metrica == "MAE" else f"{num(v / 1000, 0)}k"

    rotulo = "MAE (req/h)" if metrica == "MAE" else "MSE (req²)"
    linhas = [[rotulo, "P1", "P2", "P3", "P4"]]
    linhas += [[modelo, *[formatar(v) for v in valores]] for modelo, valores in pivo.iterrows()]
    return linhas, 1 + ordem.index("Random Forest")


# ================================================================== slides
def slide_capa(prs, capa):
    for forma in capa.shapes:
        if not forma.has_text_frame:
            continue
        texto = forma.text_frame.text
        if texto.startswith("MecaniQA"):
            ps = forma.text_frame.paragraphs
            ps[0].runs[0].text = "MecâniQA"
            for r in ps[0].runs[1:]:
                r._r.getparent().remove(r._r)
            ps[1].runs[0].text = "OAT 4: Observabilidade em Nuvem e Predição de Requisições"
            for r in ps[1].runs[1:]:
                r._r.getparent().remove(r._r)
            for r in ps[1].runs:
                r.font.size = Pt(22)
            ps[2].runs[0].text = "Computação em Nuvem e Modelos de Aprendizado de Máquina"
            for r in ps[2].runs[1:]:
                r._r.getparent().remove(r._r)
        elif texto.startswith("Autor:"):
            autores = forma
    # "Autores:" numa caixa e os nomes noutra, lado a lado: os 5 nomes ficam na mesma coluna.
    x, y = autores.left.inches, autores.top.inches
    autores._element.getparent().remove(autores._element)
    caixa(capa, x, y, 1.0, 0.4, "Autores:", tamanho=12, negrito_primeira=True)
    caixa(capa, x + 0.85, y, 4.5, 1.5, EQUIPE, tamanho=12)
    notas(capa, "Apresentador 1, abertura (20 s): Boa noite, professor. Somos a equipe Macapá. "
                "Nesta OAT 4 colocamos a API da MecâniQA sob observabilidade e criamos um motor que prevê "
                "as requisições com sucesso e com erro da próxima hora.")


def slide_agenda(agenda):
    itens = {
        "1.": ("1. Contexto e arquitetura", "Problema da MecâniQA e a pilha API → Prometheus → Grafana"),
        "2.": ("2. Observabilidade", "Ambiente rodando e os 2 dashboards no Grafana"),
        "3.": ("3. Coleta de 3 dias", "72 horas de métricas reais da API sob tráfego simulado"),
        "4.": ("4. Baselines e partições", "7 preditores de referência, MAE e MSE em 4 partições"),
        "5.": ("5. Modelo de ML e conclusões", "Feature engineering, Random Forest e comparação crítica"),
    }
    for forma in agenda.shapes:
        if not forma.has_text_frame:
            continue
        texto = forma.text_frame.text
        chave = texto[:2]
        if chave in itens:
            ps = forma.text_frame.paragraphs
            definir_paragrafo(ps[0], itens[chave][0])
            if len(ps) > 1:
                definir_paragrafo(ps[1], itens[chave][1])
        elif texto.startswith("Objetivo"):
            ps = forma.text_frame.paragraphs
            definir_paragrafo(ps[1], "O objetivo dessa apresentação é demonstrar como monitoramos a API da "
                                     "MecâniQA e prevemos as requisições com sucesso e com erro, hora a hora.")
            forma.top, forma.height = Inches(3.2), Inches(1.9)
    notas(agenda, "Apresentador 1 (15 s): Primeiro o contexto e a arquitetura; depois o ambiente, os dashboards "
                  "e a coleta; em seguida os baselines e as partições; por fim o Random Forest e as conclusões.")


def definir_paragrafo(p, texto):
    if p.runs:
        p.runs[0].text = texto
        for r in p.runs[1:]:
            r._r.getparent().remove(r._r)
    else:
        p.text = texto


def slide_contexto(s):
    titulo(s, "O problema da MecâniQA")
    problemas = [("Picos", "lentidão no horário comercial"), ("Falhas", "rajadas de erros 4xx e 5xx"),
                 ("Ociosidade", "máquina sobrando de madrugada")]
    for i, (palavra, frase) in enumerate(problemas):
        x = 0.45 + i * 3.08
        cartao(s, x, 1.3, 2.9, 1.45, palavra, [frase], tam_titulo=24, tam_corpo=12)
    cartao(s, 0.45, 3.0, 9.1, 1.45, "Objetivo do MVP na Fase 4",
           ["Ver a API em tempo real e prever a próxima hora de sucessos e erros, para escalar antes do pico."],
           fundo=VERDE_CLARO, cor_titulo=VERDE, tam_titulo=16, tam_corpo=14)
    fonte(s, "Fonte: enunciado da OAT 4, Programa de Trainee MecâniQA 2026.2")
    notas(s, "Apresentador 1 (45 s): A MecâniQA passou a receber requisições das oficinas o dia todo. Isso trouxe "
             "três problemas: picos de tráfego que deixam a API lenta no horário comercial, rajadas de erros 4xx e "
             "5xx, e máquina sobrando de madrugada. O MVP desta fase observa a API em tempo real e prevê sucessos e "
             "erros da próxima hora, para escalar antes do pico.")


def slide_arquitetura(s):
    titulo(s, "Arquitetura de observabilidade")
    blocos = [("Gerador de tráfego", "oficinas parceiras\n24 h por dia"),
              ("API Django", "/api/manutencoes/\n/metrics"),
              ("Prometheus", "coleta a cada 5 s\nretenção de 15 dias"),
              ("Grafana", "2 dashboards\nsucesso e erro")]
    for i, (t, c) in enumerate(blocos):
        x = 0.45 + i * 2.35
        cartao(s, x, 1.3, 2.0, 0.95, t, c.split("\n"), tam_titulo=12, tam_corpo=10)
        if i:
            seta(s, x - 0.33, 1.77, x - 0.04, 1.77)
    cartao(s, 5.15, 2.65, 2.0, 0.85, "Coleta", ["query_range 1 h → CSV"], fundo=VERDE_CLARO,
           cor_titulo=VERDE, tam_titulo=12, tam_corpo=10)
    cartao(s, 7.5, 2.65, 2.0, 0.85, "Motor preditivo", ["7 baselines + RF"], fundo=VERDE_CLARO,
           cor_titulo=VERDE, tam_titulo=12, tam_corpo=10)
    seta(s, 6.15, 2.27, 6.15, 2.62)
    seta(s, 7.17, 3.07, 7.47, 3.07)
    caixa(s, 0.45, 2.65, 4.4, 0.9, ["Contadores Prometheus na API:", "requests_success_total",
                                    "requests_error_total"], tamanho=9, negrito_primeira=True)
    destaque(s, 0.45, 3.75, 9.1, "4 containers no Docker Compose; o gerador reinicia sozinho após queda de energia")
    fonte(s, "Fonte: oat4/app-monitoring/docker-compose.yml. API e contadores fornecidos pelo professor")
    notas(s, "Apresentador 1 (50 s): O gerador simula as oficinas chamando a API Django. Cada resposta incrementa "
             "um contador: sucesso para 2xx e erro para 4xx/5xx. O Prometheus lê /metrics a cada 5 segundos e o "
             "Grafana mostra os dashboards. Da API do Prometheus exportamos a série por hora para os modelos.")


def slide_ambiente(s):
    titulo(s, "Ambiente em funcionamento")
    # Prints largos e baixos: um embaixo do outro, quase na largura do slide, legenda à direita.
    imagem_ou_espaco(s, PRINTS / "ambiente_docker.png", 0.3, 1.2, 7.5, 1.65,
                     "print do terminal: docker compose ps (4 serviços Up)  →  prints/ambiente_docker.png")
    imagem_ou_espaco(s, PRINTS / "ambiente_targets.png", 0.3, 3.0, 7.5, 1.65,
                     "print do Prometheus › Status › Targets (API UP)  →  prints/ambiente_targets.png")
    caixa(s, 7.95, 1.2, 1.75, 1.65, ["Docker Compose", "api, gerador, prometheus e grafana: todos Up"],
          tamanho=11, cor=VERDE, negrito_primeira=True, ancora=MSO_ANCHOR.MIDDLE)
    caixa(s, 7.95, 3.0, 1.75, 1.65, ["Prometheus", "raspa a API a cada 5 s: alvo UP"],
          tamanho=11, cor=VERDE, negrito_primeira=True, ancora=MSO_ANCHOR.MIDDLE)
    fonte(s, "Fonte: docker compose ps e http://localhost:9090/targets")
    notas(s, "Apresentador 2 (40 s): Subimos a pilha com docker compose: API, Prometheus, Grafana e o gerador de "
             "tráfego, os quatro ativos. No Prometheus, o alvo da API aparece como UP, ou seja, as métricas estão "
             "sendo raspadas a cada 5 segundos.")


def slide_dashboard(s, tipo):
    sucesso = tipo == "sucesso"
    titulo(s, f"Dashboard {'1: sucesso (2xx)' if sucesso else '2: erro (4xx/5xx)'}")
    # Print grande: praticamente o slide inteiro abaixo do título.
    imagem_ou_espaco(s, PRINTS / f"dashboard_{tipo}.png", 0.3, 1.15, 9.4, 3.5,
                     f"print do dashboard (3 a 4 painéis, últimos 3 dias, data e hora)  →  prints/dashboard_{tipo}.png")
    metrica = "success" if sucesso else "error"
    fonte(s, f"PromQL: sum(increase(mecaniqa_api_requests_{metrica}_total[1h])). "
             f"Grafana › MecâniQA › Requisições com {'Sucesso' if sucesso else 'Erro'}")
    notas(s, f"Apresentador 2 (40 s): Este é o dashboard de {'sucesso' if sucesso else 'erro'}, nos últimos 3 dias. "
             + ("Cada barra é uma hora. Dá para ver o ciclo diário: o volume sobe de manhã, tem picos perto das 10 h "
                "e das 15 h e cai de madrugada. A consulta é o increase do contador de sucesso em janelas de 1 hora."
                if sucesso else "Aqui separamos erros do cliente, 4xx, de falhas internas, 5xx. Os surtos de erro "
                "aparecem como picos isolados: são os momentos que mais pesam no MSE dos modelos."))


def slide_coleta(s, r):
    titulo(s, "Coleta de 3 dias")
    if r["tem_dados"]:
        numeros = [(f"{r['horas']} h", "exportadas"), ("72 h", "avaliadas (3 dias)"),
                   (num(r["total_sucesso"], 0), "sucessos nas 72 h"), (num(r["total_erro"], 0), "erros nas 72 h")]
        periodo = f"{r['inicio']:%d/%m %H:%M} a {r['fim']:%d/%m %H:%M} (UTC-3), horas sem dado: {r['faltantes']}"
    else:
        numeros = [("[96] h", "exportadas"), ("72 h", "avaliadas (3 dias)"),
                   ("[nº]", "sucessos nas 72 h"), ("[nº]", "erros nas 72 h")]
        periodo = "Período: [dd/mm hh:mm] a [dd/mm hh:mm] (UTC-3), horas sem dado: [0]"
    for i, (valor, rotulo) in enumerate(numeros):
        caixa(s, 0.45 + i * 2.32, 1.15, 2.2, 0.5, valor, tamanho=22, cor=VERDE if i == 1 else PRETO,
              negrito_primeira=True)
        caixa(s, 0.45 + i * 2.32, 1.62, 2.2, 0.3, rotulo, tamanho=9, cor=CINZA_TEXTO)
    # Preferência: print real do Grafana com os 3 dias; sem ele, o gráfico gerado da série exportada.
    print_grafana = localizar_imagem(PRINTS / "coleta_grafana_3dias.png")
    imagem_ou_espaco(s, print_grafana or RESULTADOS / "01_serie_coletada.png", 0.3, 2.0, 9.4, 2.65,
                     "print do Grafana com os 3 dias completos  →  prints/coleta_grafana_3dias.png")
    fonte(s, f"{periodo}. Fonte: coleta/coletar_prometheus.py (increase por hora)")
    notas(s, "Apresentador 2 (45 s): Deixamos o gerador rodando por quatro dias seguidos e exportamos do Prometheus "
             "uma linha por hora. As métricas são reais, medidas na API; o tráfego vem do gerador que simula as "
             "oficinas. O primeiro dia é só histórico, porque o lag de 24 horas precisa do dia anterior; "
             "os três últimos dias, 72 horas, são a janela avaliada. Não houve buraco na coleta "
             "(ou: houve X horas sem dado; repetimos a hora anterior só para calcular os lags e deixamos essas horas fora do MAE e do MSE).")


def slide_baselines(s):
    titulo(s, "7 preditores de baseline")
    tabela(s, 0.45, 1.3, 5.6, [["Baseline", "Previsão para a hora t"],
                                ["Lag 1 h", "valor de 1 hora antes"],
                                ["Lag 3 h", "valor de 3 horas antes"],
                                ["Lag 12 h", "valor de 12 horas antes"],
                                ["Lag 24 h", "mesma hora de ontem"],
                                ["Média móvel 3 h", "média das 3 horas anteriores"],
                                ["Média móvel 12 h", "média das 12 horas anteriores"],
                                ["Média móvel 24 h", "média das 24 horas anteriores"]], [2.0, 3.6], tamanho=10,
           destaque_linha=4)
    cartao(s, 6.35, 1.3, 3.2, 2.4, "Por que o lag de 24 h importa",
           ["Mesma hora de ontem = ciclo diário (picos ~10 h e 15 h) sem treino nenhum."],
           fundo=VERDE_CLARO, cor_titulo=VERDE, tam_corpo=10)
    destaque(s, 0.45, 3.85, 9.1, "Todas as previsões usam apenas horas anteriores (shift antes do rolling)", 12)
    fonte(s, "Fonte: analise/analise_oat4.py, função prever_baselines()")
    notas(s, "Apresentador 3 (50 s): Os baselines são regras simples, sem treino. Os lags repetem um valor passado; "
             "as médias móveis fazem a média das últimas horas. O destaque é o lag de 24 horas, que compara a mesma "
             "hora de ontem e por isso captura o ciclo diário do tráfego.")


def slide_particoes(s):
    titulo(s, "Avaliação em 4 partições")
    x0, largura_total = 0.45, 9.1
    escala = largura_total / 96
    hist = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x0), Inches(1.35), Inches(24 * escala - 0.05), Inches(1.92))
    hist.fill.solid(); hist.fill.fore_color.rgb = CINZA_CARD; hist.line.fill.background(); hist.shadow.inherit = False
    caixa(s, x0, 1.35, 24 * escala - 0.05, 1.92, ["24 h de", "histórico", "(não avaliado)"], tamanho=10, cor=CINZA_TEXTO,
          alinhar=PP_ALIGN.CENTER, ancora=MSO_ANCHOR.MIDDLE)
    for i, horas in enumerate((18, 36, 54, 72)):
        y = 1.35 + i * 0.5
        barra = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x0 + 24 * escala), Inches(y),
                                   Inches(horas * escala), Inches(0.42))
        barra.fill.solid()
        barra.fill.fore_color.rgb = VERDE if i == 3 else VERDE_CLARO
        barra.line.fill.background(); barra.shadow.inherit = False
        caixa(s, x0 + 24 * escala, y, horas * escala, 0.42, f"P{i + 1}: primeiras {horas} h",
              tamanho=10, cor=BRANCO if i == 3 else VERDE, negrito_primeira=True, ancora=MSO_ANCHOR.MIDDLE)
    cartao(s, 0.45, 3.4, 4.45, 1.15, "MAE (erro médio absoluto)",
           ["Quantas requisições por hora o modelo erra, em média."], tam_titulo=12, tam_corpo=10)
    cartao(s, 5.1, 3.4, 4.45, 1.15, "MSE (erro quadrático médio)",
           ["Eleva o erro ao quadrado: pune mais os grandes desvios (surtos)."], tam_titulo=12, tam_corpo=10)
    fonte(s, "Cada modelo × partição × série (sucesso e erro) gera um MAE e um MSE. Fonte: analise/analise_oat4.py")
    notas(s, "Apresentador 3 (45 s): Dividimos as 72 horas em quatro partições acumuladas: 18, 36, 54 e 72 horas. "
             "Assim vemos se o erro muda conforme o histórico cresce. Para cada partição calculamos MAE, que é o erro "
             "médio em requisições, e MSE, que castiga mais os erros grandes.")


def slide_resultado(s, r, serie):
    rotulo = "sucesso" if serie == "sucesso" else "erro"
    titulo(s, f"Resultados: {rotulo}")
    if r["tem_metricas"]:
        for k, metrica in enumerate(("MAE", "MSE")):
            linhas, destaque_i = tabela_particoes(r, serie, metrica)
            tabela(s, 0.3 + k * 4.75, 1.15, 4.6, linhas, [1.6, 0.75, 0.75, 0.75, 0.75], tamanho=9,
                   destaque_linha=destaque_i, numeros_a_direita=True)
        info = r[serie]
        conclusao = (f"Melhor: {info['melhor_baseline']} (MAE {num(info['mae_baseline'])}); "
                     f"Random Forest: MAE {num(info['mae_rf'])}, {info['posicao_rf']}º de 8 em P4")
        fala = (f"Na tabela da esquerda está o MAE e na da direita o MSE, das quatro partições, do melhor para o pior. "
                f"O melhor foi o {info['melhor_baseline']}, com erro médio de {num(info['mae_baseline'])} requisições "
                f"por hora nas 72 horas. O Random Forest, na linha verde, ficou em {info['posicao_rf']}º lugar, com MAE "
                f"{num(info['mae_rf'])}. O MSE confirma a ordem e pesa mais os picos.")
    else:
        imagem_ou_espaco(s, None, 0.3, 1.15, 4.6, 2.75, "tabela MAE × partição  →  gerada pela análise")
        imagem_ou_espaco(s, None, 5.05, 1.15, 4.6, 2.75, "tabela MSE × partição  →  gerada pela análise")
        conclusao = "Melhor: [modelo] (MAE [x]); Random Forest: MAE [y], [n]º de 8 em P4"
        fala = "Leiam a tabela: qual modelo foi o melhor, em que posição ficou o Random Forest e o que o MSE mostra."
    destaque(s, 0.3, 4.1, 9.4, conclusao, 12)
    fonte(s, f"MAE em requisições/hora; MSE em milhares (k) de req². Menor é melhor. "
             f"resultados/tabela_mae_{serie}.csv e tabela_mse_{serie}.csv")
    notas(s, f"Apresentador {'3' if serie == 'sucesso' else '4'} (60 s): " + fala)


def slide_execucao(s, r):
    titulo(s, "Análise executada")
    # Print real do terminal (apresentacao/capturar_prints.py --analise), o mais alto possível.
    imagem_ou_espaco(s, PRINTS / "analise_terminal.png", 0.3, 1.1, 6.4, 3.6,
                     "print do terminal rodando analise_oat4.py  →  capturar_prints.py --analise")
    if r["tem_metricas"]:
        itens = []
        for serie in ("sucesso", "erro"):
            info = r[serie]
            itens += [f"{serie.capitalize()}", f"melhor: {info['melhor_baseline']}, MAE {num(info['mae_baseline'])}",
                      f"Random Forest: {info['posicao_rf']}º de 8, MAE {num(info['mae_rf'])}", ""]
    else:
        itens = ["Sucesso", "melhor: [modelo], MAE [x]", "Random Forest: [n]º de 8, MAE [y]", "",
                 "Erro", "melhor: [modelo], MAE [x]", "Random Forest: [n]º de 8, MAE [y]", ""]
    tb = caixa(s, 6.85, 1.3, 2.95, 3.2, itens[:-1], tamanho=10, cor=PRETO, ancora=MSO_ANCHOR.MIDDLE)
    for i, par in enumerate(tb.text_frame.paragraphs):
        if i in (0, 4):
            for run in par.runs:
                run.font.bold = True
                run.font.color.rgb = VERDE
                run.font.size = Pt(14)
    fonte(s, "Execução real de analise/analise_oat4.py sobre dados/serie_horaria.csv, partição P4 (72 h), ordenado por MAE")
    notas(s, "Apresentador 4 (30 s): Este é o terminal com a análise rodando de verdade sobre os dados coletados. "
             "O script lê a série horária, calcula os sete baselines e o Random Forest e imprime o ranking da "
             "partição de 72 horas, para sucesso e para erro. As tabelas que mostramos saem desta execução.")


def slide_features(s):
    titulo(s, "Feature engineering")
    grupos = [("Calendário", "hora e período do dia", "o tráfego segue o relógio"),
              ("Memória", "lags de 1, 2, 3 e 24 h", "inércia e ciclo diário"),
              ("Janelas", "média e desvio 3–24 h", "nível e volatilidade"),
              ("Tendência", "variação e outra série", "subida/queda e efeito cruzado")]
    for i, (nome, itens, porque) in enumerate(grupos):
        cartao(s, 0.3 + i * 2.37, 1.15, 2.25, 1.05, nome, [itens, porque], tam_titulo=12, tam_corpo=9)
    for k, serie in enumerate(("sucesso", "erro")):
        imagem_ou_espaco(s, RESULTADOS / f"05_importancia_features_{serie}.png", 0.3 + k * 4.75, 2.32, 4.6, 2.33,
                         f"importância das features ({serie})  →  resultados/05_importancia_features_{serie}.png")
    fonte(s, "Só horas anteriores (shift). Sem dia da semana: em 4 dias cada dia aparece 1 vez. "
             "Fonte: analise/analise_oat4.py, criar_features()")
    notas(s, "Apresentador 4 (50 s): Transformamos a série em colunas que o modelo entende. Calendário, porque o "
             "tráfego depende da hora; memória, com os lags, incluindo a mesma hora de ontem; janelas, com média e "
             "desvio, que medem nível e instabilidade; e tendência, com a variação de uma hora para outra e a outra "
             "série. Não usamos dia da semana: com só quatro dias de dados, cada dia apareceria uma vez. Todas as "
             "features usam só o passado. Os gráficos mostram em quais o Random Forest mais se apoiou.")


def slide_modelo(s, r, serie="sucesso"):
    titulo(s, f"RF × baselines: {serie}")
    imagem_ou_espaco(s, RESULTADOS / f"03_previsoes_{serie}.png", 0.3, 1.15, 9.4, 1.75,
                     f"real × melhor baseline × RF  →  resultados/03_previsoes_{serie}.png")
    imagem_ou_espaco(s, RESULTADOS / f"04_evolucao_mae_{serie}.png", 0.3, 2.95, 9.4, 1.72,
                     f"evolução do MAE por partição  →  resultados/04_evolucao_mae_{serie}.png")
    fonte(s, "Walk-forward: a cada hora o RF (300 árvores) treina só com as horas anteriores e prevê a seguinte")
    info = r.get(serie, {}) if r.get("tem_metricas") else {}
    if info:
        fala = (f"No primeiro gráfico, a linha preta é o real; a tracejada, o {info['melhor_baseline']}; a laranja, o "
                f"Random Forest. No segundo, o MAE de cada modelo por partição: o do Random Forest foi de "
                f"{num(info['rf_p1'])} em P1 para {num(info['rf_p4'])} em P4.")
    else:
        fala = "Expliquem os dois gráficos: real × previsões e a evolução do MAE de P1 a P4."
    notas(s, f"Apresentador 5 (45 s): O Random Forest foi avaliado em walk-forward: a cada hora ele treina só com o "
             f"passado e prevê a hora seguinte, sem ver o futuro. {fala}")


def slide_conclusao(s, r):
    titulo(s, "Considerações finais")
    tem = r["tem_metricas"]
    for i, serie in enumerate(("sucesso", "erro")):
        info = r.get(serie, {})
        y = 1.15 + i * 1.0
        caixa(s, 0.45, y + 0.2, 1.4, 0.5, serie.capitalize(), tamanho=16, negrito_primeira=True)
        blocos = [(f"MAE {num(info['mae_baseline'])}" if tem else "MAE [x]",
                   f"melhor baseline: {info['melhor_baseline']}" if tem else "melhor baseline: [modelo]", VERDE),
                  (f"MAE {num(info['mae_rf'])}" if tem else "MAE [y]", "Random Forest", PRETO)]
        for j, (valor, rotulo, cor) in enumerate(blocos):
            x = 2.0 + j * 3.8
            caixa(s, x, y, 3.6, 0.55, valor, tamanho=24, cor=cor, negrito_primeira=True)
            caixa(s, x, y + 0.55, 3.6, 0.32, rotulo, tamanho=10, cor=CINZA_TEXTO)
    # Por que o modelo ganhou ou perdeu: frase montada com os números medidos.
    if tem:
        su = r["sucesso"]
        top = su.get("top_features", ["?"])[0]
        peso = su.get("top_peso", 0)
        if su["rf_venceu"]:
            porque = (f"Por quê: o RF combinou {top} ({peso:.0%} da importância) com o calendário e superou o "
                      f"{su['melhor_baseline']}.")
        else:
            porque = (f"Por quê: o RF se apoiou quase só em {top} ({peso:.0%} da importância) e teve poucas horas de "
                      f"treino; o {su['melhor_baseline']} já captura o ciclo diário sem treino.")
    else:
        porque = "Por quê: [o RF se apoiou em (feature) e teve poucas horas de treino / combinou features e venceu]."
    caixa(s, 0.45, 3.2, 9.1, 0.6, porque, tamanho=12)
    destaque(s, 0.45, 3.85, 9.1, "Observabilidade + previsão: escalar antes do pico. Próximo passo: mais dias de coleta", 13)
    fonte(s, "MAE na partição P4 (72 h), em requisições por hora. Fonte: resultados/metricas_todas.csv")
    if tem:
        su, er = r["sucesso"], r["erro"]
        fala = (f"Em sucesso, o melhor foi o {su['melhor_baseline']}, com MAE {num(su['mae_baseline'])}; o Random "
                f"Forest teve {num(su['mae_rf'])}. Em erro, {er['melhor_baseline']} com {num(er['mae_baseline'])} "
                f"contra {num(er['mae_rf'])} do Random Forest. {porque[9:]} Com mais dias de coleta, o modelo veria "
                "cada hora do dia várias vezes e poderia superar o baseline.")
    else:
        fala = "Comparem o melhor baseline com o Random Forest nas duas séries e expliquem por quê."
    notas(s, f"Apresentador 5 (50 s): {fala} Obrigado, professor; ficamos à disposição para perguntas.")


def slide_referencias(s):
    for forma in s.shapes:
        if forma.has_text_frame and forma.text_frame.text.startswith("Código"):
            forma._element.getparent().remove(forma._element)
    caixa(s, 0.45, 1.25, 9.1, 3.4, [
        [("Código, dashboards e resultados", True)],
        [("github.com/LenilsonSoares/mecaniQA-nuvem-macapa (pasta oat4/)", False)],
        [("API, contadores e gerador de tráfego fornecidos pelo professor", True)],
        [("github.com/mecaniQA/app-monitoring", False)],
        [("Documentação oficial", True)],
        [("prometheus.io/docs, grafana.com/docs, scikit-learn.org/stable/modules/ensemble.html", False)],
        [("Material da disciplina", True)],
        [("OAT 4: Observabilidade em Nuvem e Predição de Requisições; aulas de séries temporais e métricas", False)],
    ], tamanho=12)


# ===================================================================== main
def exportar_pdf(pptx, pdf):
    """Exporta o PDF pelo PowerPoint (Windows). No Google Slides: Arquivo › Fazer download › PDF."""
    script = (
        "$a = New-Object -ComObject PowerPoint.Application; "
        f"$p = $a.Presentations.Open('{Path(pptx).resolve()}', $true, $false, $false); "
        f"$p.SaveAs('{Path(pdf).resolve()}', 32); $p.Close(); $a.Quit()"
    )
    resultado = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True)
    if resultado.returncode != 0 or not Path(pdf).is_file():
        print("Não foi possível exportar pelo PowerPoint. Abra o .pptx no Google Slides e baixe como PDF.")
        return False
    print(f"PDF exportado: {pdf}")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pdf", action="store_true", help="também exporta o PDF pelo PowerPoint (Windows)")
    args = parser.parse_args()
    prs = Presentation(MODELO)
    originais = list(prs.slides)
    capa, agenda, base, refs_modelo = originais[0], originais[1], originais[2], originais[-1]
    resumo = carregar_resumo()

    slide_capa(prs, capa)
    slide_agenda(agenda)
    construtores = [
        slide_contexto, slide_arquitetura, slide_ambiente,
        lambda s: slide_dashboard(s, "sucesso"), lambda s: slide_dashboard(s, "erro"),
        lambda s: slide_coleta(s, resumo), slide_baselines, slide_particoes,
        lambda s: slide_resultado(s, resumo, "sucesso"), lambda s: slide_resultado(s, resumo, "erro"),
        lambda s: slide_execucao(s, resumo), slide_features,
        lambda s: slide_modelo(s, resumo, "sucesso"), lambda s: slide_modelo(s, resumo, "erro"),
        lambda s: slide_conclusao(s, resumo),
    ]
    for construir in construtores:
        s = clonar_slide(prs, base)
        limpar_conteudo(s)
        construir(s)
    refs = clonar_slide(prs, refs_modelo)
    limpar_conteudo(refs)
    slide_referencias(refs)

    for antigo in originais[2:]:
        remover_slide(prs, antigo)

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    prs.save(SAIDA)
    estado = ("com dados reais" if resumo["tem_metricas"] else "com espaços reservados (rode a coleta e a análise)")
    print(f"Apresentação gerada {estado}: {SAIDA}")
    if args.pdf and sys.platform.startswith("win"):
        # Sem dados reais o PDF é só rascunho: o nome deixa claro para ninguém enviar por engano.
        nome_pdf = SAIDA.with_suffix(".pdf") if resumo["tem_metricas"] else SAIDA.with_name(SAIDA.stem + "_RASCUNHO.pdf")
        exportar_pdf(SAIDA, nome_pdf)
    else:
        print("Abra no Google Slides (fonte Poppins do modelo) e exporte como mecaniQA_oat4_macapa.pdf.")


if __name__ == "__main__":
    main()
