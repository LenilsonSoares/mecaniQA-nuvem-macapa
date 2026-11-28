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


def formula(slide, x, y, w, h, linhas, tamanho=12):
    """Fórmula num quadro claro, em fonte monoespaçada para alinhar os símbolos."""
    forma = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    forma.adjustments[0] = 0.08
    forma.fill.solid()
    forma.fill.fore_color.rgb = BRANCO
    forma.line.color.rgb = CINZA_BORDA
    forma.shadow.inherit = False
    tb = caixa(slide, x + 0.1, y, w - 0.2, h, linhas, tamanho=tamanho, ancora=MSO_ANCHOR.MIDDLE)
    for p in tb.text_frame.paragraphs:
        for r in p.runs:
            r.font.name = "Consolas"
    return tb


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
            # Posição do lag 24 h, citada nas considerações finais.
            lag24 = final[final["modelo"].str.startswith("Lag 24")]
            if len(lag24):
                info["lag24"] = {"posicao": 1 + list(final["modelo"]).index(lag24.iloc[0]["modelo"]),
                                 "mae": lag24.iloc[0]["MAE"]}
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
        "3.": ("3. Coleta de 96 horas", "1 dia de histórico + 72 h avaliadas"),
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
    caixa(s, 0.45, 4.55, 9.1, 0.35, "Clientes: oficinas e auto centers de Feira de Santana e região, "
          "com o sistema já em operação na nuvem", tamanho=11, cor=CINZA_TEXTO)
    notas(s, "Apresentador 1 (45 s): A MecâniQA atende oficinas e auto centers de Feira de Santana e região. Na Fase 4 "
             "o sistema já está na nuvem e recebe requisições das oficinas o dia todo. Isso trouxe "
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
    caixa(s, 0.45, 2.65, 4.5, 0.9, ["Contadores da API:", "mecaniqa_api_requests_success_total",
                                    "mecaniqa_api_requests_error_total"], tamanho=10, negrito_primeira=True)
    destaque(s, 0.45, 3.75, 9.1, "4 containers no Docker Compose, todos com restart: unless-stopped")
    notas(s, "Apresentador 1 (50 s): O gerador simula as oficinas chamando a API Django. Cada resposta incrementa "
             "um contador: success para 2xx e error para 4xx/5xx. O Prometheus lê /metrics a cada 5 segundos e o "
             "Grafana mostra os dashboards. Da API do Prometheus exportamos a série por hora para os modelos. "
             "Os quatro containers têm restart unless-stopped: se o Docker reiniciar, eles voltam sozinhos.")


def slide_ambiente(s):
    titulo(s, "Ambiente em funcionamento")
    # Prints largos e baixos: um embaixo do outro, quase na largura do slide, legenda à direita.
    imagem_ou_espaco(s, PRINTS / "ambiente_docker.png", 0.3, 1.2, 7.5, 1.65,
                     "print do terminal: docker compose ps (4 serviços Up)  →  prints/ambiente_docker.png")
    imagem_ou_espaco(s, PRINTS / "ambiente_targets.png", 0.3, 3.0, 7.5, 1.65,
                     "print do Prometheus › Status › Targets (API UP)  →  prints/ambiente_targets.png")
    caixa(s, 7.95, 1.2, 1.75, 1.65, ["Docker Compose", "api, gerador, prometheus e grafana: todos Up"],
          tamanho=11, cor=VERDE, negrito_primeira=True, ancora=MSO_ANCHOR.MIDDLE)
    caixa(s, 7.95, 3.0, 1.85, 0.35, "prometheus.yml", tamanho=11, cor=VERDE, negrito_primeira=True)
    formula(s, 7.95, 3.38, 1.85, 1.27, ["scrape_interval: 5s", "job_name:", " mecaniqa-django-api",
                                        "targets: api:8000"], tamanho=8)
    notas(s, "Apresentador 2 (40 s): Subimos a pilha com docker compose: API, Prometheus, Grafana e o gerador de "
             "tráfego, os quatro ativos. No prometheus.yml configuramos o job mecaniqa-django-api, que lê a API na "
             "porta 8000 a cada 5 segundos. Na tela de Targets ele aparece como UP: as métricas estão sendo raspadas.")


# Painéis do Grafana que viram slide (mesmos ids de apresentacao/capturar_prints.py), com a fala de cada um.
PAINEIS = {
    "sucesso": [
        (5, "por hora",
         "Este é o painel principal do dashboard de sucesso, com os dias da coleta. Cada ponto é o total de "
         "requisições com sucesso em uma hora: é exatamente essa série que exportamos para os modelos. "
         "Dá para ver o ciclo diário: sobe durante o dia e cai de madrugada. A consulta é o increase do "
         "contador de sucesso em janelas de 1 hora."),
        (6, "por minuto",
         "Aqui o mesmo contador em tempo real, em requisições por minuto, com rate de 5 minutos. "
         "É o painel que a equipe de operação olharia para perceber um pico chegando."),
        (7, "por status",
         "E aqui os sucessos separados por código de status, 200, 201 e 202, usando o rótulo status_code "
         "do contador."),
    ],
    "erro": [
        (5, "por hora",
         "No dashboard de erro, o painel principal é o total de erros 4xx e 5xx por hora, a segunda série que "
         "os modelos tentam prever. Os surtos aparecem como picos isolados: são as horas que mais pesam no MSE."),
        (6, "4xx × 5xx",
         "Este painel separa erros do cliente, 4xx, de falhas internas da API, 5xx, pelo rótulo error_class."),
        (7, "taxa de erro",
         "E esta é a taxa de erro: erros divididos pelo total de requisições. Os surtos de falha viram picos "
         "nesta curva."),
    ],
}


def slide_painel(s, tipo, painel, nome, fala):
    sucesso = tipo == "sucesso"
    titulo(s, f"Dashboard {'sucesso' if sucesso else 'erro'}: {nome}")
    # Um painel por slide, ocupando a área inteira abaixo do título.
    imagem_ou_espaco(s, PRINTS / f"painel_{tipo}_{painel}.png", 0.3, 1.15, 9.4, 3.7,
                     f"painel {painel} do Grafana  →  capturar_prints.py gera prints/painel_{tipo}_{painel}.png")
    notas(s, f"Apresentador 2 (20 s): {fala}")


def slide_coleta(s, r):
    titulo(s, "Coleta de 96 horas")
    if r["tem_dados"]:
        numeros = [(f"{r['horas']} h", "exportadas"), ("72 h", "avaliadas (3 dias)"),
                   (num(r["total_sucesso"], 0), "sucessos nas 72 h"), (num(r["total_erro"], 0), "erros nas 72 h")]
        periodo = f"{r['inicio']:%d/%m %H:%M} a {r['fim']:%d/%m %H:%M}"
        faltantes = r["faltantes"]
    else:
        numeros = [("[96] h", "exportadas"), ("72 h", "avaliadas (3 dias)"),
                   ("[nº]", "sucessos nas 72 h"), ("[nº]", "erros nas 72 h")]
        periodo, faltantes = "[dd/mm hh:mm] a [dd/mm hh:mm]", None
    for i, (valor, rotulo) in enumerate(numeros):
        caixa(s, 0.45 + i * 2.32, 1.15, 2.2, 0.5, valor, tamanho=22, cor=VERDE if i == 1 else PRETO,
              negrito_primeira=True)
        caixa(s, 0.45 + i * 2.32, 1.62, 2.2, 0.3, rotulo, tamanho=10, cor=CINZA_TEXTO)
    cartao(s, 0.45, 2.2, 4.45, 1.95, "Por que 96 h e não 72 h",
           ["As primeiras 24 h são só histórico.",
            "Assim o lag 24 h já tem a mesma hora de ontem desde a 1ª hora avaliada (partição P1)."],
           fundo=VERDE_CLARO, cor_titulo=VERDE, tam_titulo=14, tam_corpo=12)
    if faltantes == 0:
        buracos = ["Nenhuma hora faltou na coleta.",
                   "Se faltasse: repetimos a hora anterior só para os lags e tiramos essa hora (e as 24 h "
                   "seguintes) do MAE e do MSE."]
    else:
        buracos = [f"{faltantes if faltantes is not None else '[n]'} hora(s) sem dado.",
                   "Repetimos a hora anterior só para os lags e tiramos essa hora (e as 24 h seguintes) do MAE "
                   "e do MSE."]
    cartao(s, 5.1, 2.2, 4.45, 1.95, "Horas sem dado (missing values)", buracos, tam_titulo=14, tam_corpo=12)
    caixa(s, 0.45, 4.3, 9.1, 0.3, f"Período: {periodo} (horário de Brasília), uma linha por hora",
          tamanho=10, cor=CINZA_TEXTO)
    sem_buraco = ("Não houve buraco na coleta, mas o código já trata: se faltar uma hora, repetimos a hora "
                  "anterior só para calcular os lags e deixamos essa hora e as 24 seguintes fora do MAE e do MSE."
                  if faltantes == 0 else
                  "Houve horas sem dado: repetimos a hora anterior só para calcular os lags, sem usar o futuro, e "
                  "deixamos essas horas e as 24 seguintes fora do MAE e do MSE, para todos os modelos.")
    notas(s, "Apresentador 2 (45 s): Deixamos o gerador rodando por quatro dias seguidos e exportamos do Prometheus "
             "uma linha por hora. Por que 96 e não 72 horas? Porque o lag de 24 horas precisa da mesma hora do dia "
             "anterior. Se tivéssemos só 72 horas, ele ficaria sem valor nas primeiras 24, ou seja, a partição P1 "
             "inteira ficaria sem previsão. Então o primeiro dia é só histórico e os três últimos são avaliados. "
             + sem_buraco)


def slide_baselines(s):
    titulo(s, "7 preditores de baseline")
    tabela(s, 0.45, 1.3, 5.6, [["Baseline", "Previsão para a hora t"],
                                ["Lag 1 h", "valor de 1 hora antes"],
                                ["Lag 3 h", "valor de 3 horas antes"],
                                ["Lag 12 h", "valor de 12 horas antes"],
                                ["Lag 24 h", "mesma hora de ontem"],
                                ["Média móvel 3 h", "média das 3 horas anteriores"],
                                ["Média móvel 12 h", "média das 12 horas anteriores"],
                                ["Média móvel 24 h", "média das 24 horas anteriores"]], [2.0, 3.6], tamanho=11,
           destaque_linha=4)
    caixa(s, 6.35, 1.3, 3.2, 0.35, "Lag de k horas", tamanho=12, cor=VERDE, negrito_primeira=True)
    formula(s, 6.35, 1.68, 3.2, 0.6, "ŷ(t) = y(t − k)", tamanho=14)
    caixa(s, 6.35, 2.45, 3.2, 0.35, "Média móvel de m horas", tamanho=12, cor=VERDE, negrito_primeira=True)
    formula(s, 6.35, 2.83, 3.2, 0.75, ["ŷ(t) = [y(t−1) + … + y(t−m)] / m"], tamanho=11)
    destaque(s, 0.45, 3.95, 9.1, "Nenhum baseline usa a hora que está sendo prevista: só horas anteriores", 12)
    notas(s, "Apresentador 3 (50 s): Os baselines são regras simples, sem treino. O lag de k horas repete o valor "
             "de k horas atrás; a média móvel faz a média das m horas anteriores, sem incluir a hora prevista. "
             "O destaque é o lag de 24 horas, que compara a mesma hora de ontem e por isso captura o ciclo diário "
             "do tráfego.")


def slide_particoes(s):
    titulo(s, "Avaliação em 4 partições")
    x0, largura_total = 0.45, 9.1
    escala = largura_total / 96
    hist = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x0), Inches(1.25), Inches(24 * escala - 0.05), Inches(1.72))
    hist.fill.solid(); hist.fill.fore_color.rgb = CINZA_CARD; hist.line.fill.background(); hist.shadow.inherit = False
    caixa(s, x0, 1.25, 24 * escala - 0.05, 1.72, ["24 h de", "histórico", "(lag 24 h", "já funciona", "na P1)"],
          tamanho=10, cor=CINZA_TEXTO, alinhar=PP_ALIGN.CENTER, ancora=MSO_ANCHOR.MIDDLE)
    for i, horas in enumerate((18, 36, 54, 72)):
        y = 1.25 + i * 0.44
        barra = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x0 + 24 * escala), Inches(y),
                                   Inches(horas * escala), Inches(0.38))
        barra.fill.solid()
        barra.fill.fore_color.rgb = VERDE if i == 3 else VERDE_CLARO
        barra.line.fill.background(); barra.shadow.inherit = False
        caixa(s, x0 + 24 * escala, y, horas * escala, 0.38, f"P{i + 1}: primeiras {horas} h",
              tamanho=10, cor=BRANCO if i == 3 else VERDE, negrito_primeira=True, ancora=MSO_ANCHOR.MIDDLE)
    caixa(s, 0.45, 3.1, 4.45, 0.35, "MAE (erro médio absoluto)", tamanho=12, cor=VERDE, negrito_primeira=True)
    formula(s, 0.45, 3.45, 4.45, 0.55, "MAE = média de |real − previsto|", tamanho=12)
    caixa(s, 0.45, 4.03, 4.45, 0.5, "em requisições por hora: quanto o modelo erra, em média", tamanho=10,
          cor=CINZA_TEXTO)
    caixa(s, 5.1, 3.1, 4.45, 0.35, "MSE (erro quadrático médio)", tamanho=12, cor=VERDE, negrito_primeira=True)
    formula(s, 5.1, 3.45, 4.45, 0.55, "MSE = média de (real − previsto)²", tamanho=12)
    caixa(s, 5.1, 4.03, 4.45, 0.5, "eleva o erro ao quadrado: pune mais os erros grandes (surtos)", tamanho=10,
          cor=CINZA_TEXTO)
    notas(s, "Apresentador 3 (50 s): Dividimos as 72 horas em quatro partições acumuladas: 18, 36, 54 e 72 horas. "
             "Assim vemos se o erro muda conforme o histórico cresce. Repare no bloco cinza: são as 24 horas de "
             "histórico. Sem elas, o lag de 24 horas não teria valor na P1, porque ainda não existiria o dia "
             "anterior. Para cada partição calculamos o MAE, a média do erro absoluto, em requisições, e o MSE, a "
             "média do erro ao quadrado, que castiga mais os erros grandes.")


def slide_resultado(s, r, serie, metrica):
    rotulo = "sucesso" if serie == "sucesso" else "erro"
    titulo(s, f"{metrica} por partição: {rotulo}")
    apresentador = "3" if serie == "sucesso" else "4"
    if r["tem_metricas"]:
        linhas, destaque_i = tabela_particoes(r, serie, metrica)
        tabela(s, 0.9, 1.15, 8.2, linhas, [3.0, 1.3, 1.3, 1.3, 1.3], tamanho=12,
               destaque_linha=destaque_i, numeros_a_direita=True)
        info = r[serie]
        if metrica == "MAE":
            conclusao = (f"Melhor: {info['melhor_baseline']} (MAE {num(info['mae_baseline'])} req/h). "
                         f"Random Forest: {info['posicao_rf']}º de 8 em P4")
            fala = (f"Esta é a tabela do MAE para {rotulo}, em requisições por hora, ordenada do melhor para o pior "
                    f"na P4. O melhor foi o {info['melhor_baseline']}, errando em média {num(info['mae_baseline'])} "
                    f"requisições por hora nas 72 horas. O Random Forest, na linha verde, ficou em "
                    f"{info['posicao_rf']}º lugar, com MAE {num(info['mae_rf'])}.")
        else:
            conclusao = "MSE em milhares (k) de req². Menor é melhor; pesa mais as horas de pico"
            fala = (f"E esta é a tabela do MSE para {rotulo}, na mesma ordem. Como o erro é elevado ao quadrado, "
                    "os números ficam grandes e mostramos em milhares. O MSE pesa mais as horas de pico: se um "
                    "modelo sobe aqui e não no MAE, é porque erra feio poucas horas.")
    else:
        imagem_ou_espaco(s, None, 0.9, 1.15, 8.2, 2.75, f"tabela {metrica} × partição  →  gerada pela análise")
        conclusao = ("Melhor: [modelo] (MAE [x] req/h). Random Forest: [n]º de 8 em P4" if metrica == "MAE"
                     else "MSE em milhares (k) de req². Menor é melhor; pesa mais as horas de pico")
        fala = f"Leiam a tabela do {metrica}: qual modelo foi o melhor e em que posição ficou o Random Forest."
    destaque(s, 0.9, 4.15, 8.2, conclusao, 12)
    notas(s, f"Apresentador {apresentador} (40 s): " + fala)


def slide_execucao(s, r):
    titulo(s, "Análise executada")
    # Print real do terminal (apresentacao/capturar_prints.py --analise) na largura toda do slide.
    imagem_ou_espaco(s, PRINTS / "analise_terminal.png", 0.3, 1.15, 9.4, 3.7,
                     "print do terminal rodando analise_oat4.py  →  capturar_prints.py --analise")
    notas(s, "Apresentador 4 (30 s): Este é o terminal com a análise rodando de verdade sobre os dados coletados. "
             "O script lê a série horária, calcula os sete baselines e o Random Forest e imprime o ranking da "
             "partição de 72 horas, para sucesso e para erro. As tabelas que mostramos saem desta execução.")


def slide_features(s):
    titulo(s, "Feature engineering")
    grupos = [("Calendário", "hora e período do dia", "o tráfego segue o relógio"),
              ("Memória", "lags de 1, 2, 3 e 24 h", "inércia e ciclo diário"),
              ("Janelas", "média e desvio de 3 a 24 h", "nível e volatilidade"),
              ("Tendência", "variação de 1 h e a outra série", "subida/queda e efeito cruzado")]
    for i, (nome, itens, porque) in enumerate(grupos):
        x, y = 0.45 + (i % 2) * 4.65, 1.2 + (i // 2) * 1.45
        cartao(s, x, y, 4.45, 1.3, nome, [itens, porque], tam_titulo=15, tam_corpo=12)
    destaque(s, 0.45, 4.2, 9.1, "Todas as features usam só horas anteriores. Sem dia da semana: em 4 dias, cada dia "
                                "apareceria 1 vez", 12)
    notas(s, "Apresentador 4 (50 s): Transformamos a série em colunas que o modelo entende. Calendário, porque o "
             "tráfego depende da hora; memória, com os lags, incluindo a mesma hora de ontem; janelas, com média e "
             "desvio, que medem nível e instabilidade; e tendência, com a variação de uma hora para outra e a outra "
             "série. Não usamos dia da semana: com só quatro dias de dados, cada dia apareceria uma vez. Todas as "
             "features usam só o passado.")


def slide_importancia(s, r, serie):
    titulo(s, f"Features do RF: {serie}")
    imagem_ou_espaco(s, RESULTADOS / f"05_importancia_features_{serie}.png", 0.3, 1.15, 9.4, 3.7,
                     f"importância das features ({serie})  →  resultados/05_importancia_features_{serie}.png")
    info = r.get(serie, {}) if r.get("tem_metricas") else {}
    if info.get("top_features"):
        fala = (f"A feature mais importante foi {info['top_features'][0]}, com {info['top_peso']:.0%} da importância, "
                f"seguida de {info['top_features'][1]}.")
    else:
        fala = "Digam qual feature ficou no topo e o que isso significa."
    notas(s, f"Apresentador 4 (25 s): Este gráfico mostra em quais features o Random Forest mais se apoiou para "
             f"prever {serie}. {fala}")


def slide_previsoes(s, r, serie):
    titulo(s, f"Real × previsões: {serie}")
    imagem_ou_espaco(s, RESULTADOS / f"03_previsoes_{serie}.png", 0.3, 1.15, 9.4, 3.7,
                     f"real × melhor baseline × RF  →  resultados/03_previsoes_{serie}.png")
    info = r.get(serie, {}) if r.get("tem_metricas") else {}
    if info:
        fala = (f"A linha preta é o valor real; a tracejada, o {info['melhor_baseline']}, nosso melhor baseline; "
                f"a outra, o Random Forest. As linhas pontilhadas verticais marcam as partições.")
    else:
        fala = "Expliquem as linhas: real, melhor baseline e Random Forest."
    notas(s, f"Apresentador 5 (35 s): O Random Forest foi avaliado em walk-forward: a cada hora ele treina só com o "
             f"passado e prevê a hora seguinte, sem ver o futuro. {fala}")


def slide_evolucao(s, r, serie):
    titulo(s, f"MAE de P1 a P4: {serie}")
    imagem_ou_espaco(s, RESULTADOS / f"04_evolucao_mae_{serie}.png", 0.3, 1.15, 9.4, 3.7,
                     f"evolução do MAE por partição  →  resultados/04_evolucao_mae_{serie}.png")
    info = r.get(serie, {}) if r.get("tem_metricas") else {}
    if info:
        fala = (f"O MAE do Random Forest, a linha preta grossa, foi de {num(info['rf_p1'])} em P1 para "
                f"{num(info['rf_p4'])} em P4, conforme ganhou mais horas de treino.")
    else:
        fala = "Digam se o erro do Random Forest caiu ou subiu de P1 para P4 e por quê."
    notas(s, f"Apresentador 5 (25 s): Aqui o MAE de cada modelo em cada partição, mostrando o que acontece quando o "
             f"histórico cresce. {fala}")


def slide_conclusao(s, r):
    titulo(s, "Considerações finais")
    tem = r["tem_metricas"]
    for i, serie in enumerate(("sucesso", "erro")):
        info = r.get(serie, {})
        y = 1.1 + i * 0.95
        caixa(s, 0.45, y + 0.15, 1.4, 0.5, serie.capitalize(), tamanho=16, negrito_primeira=True)
        blocos = [(f"MAE {num(info['mae_baseline'])}" if tem else "MAE [x]",
                   f"melhor baseline: {info['melhor_baseline']}" if tem else "melhor baseline: [modelo]", VERDE),
                  (f"MAE {num(info['mae_rf'])}" if tem else "MAE [y]", "Random Forest", PRETO)]
        for j, (valor, rotulo, cor) in enumerate(blocos):
            x = 2.0 + j * 3.8
            caixa(s, x, y, 3.6, 0.5, valor, tamanho=22, cor=cor, negrito_primeira=True)
            caixa(s, x, y + 0.5, 3.6, 0.3, rotulo, tamanho=10, cor=CINZA_TEXTO)
    # Por que o modelo ganhou ou perdeu: frase montada com os números medidos.
    if tem:
        su = r["sucesso"]
        top = su.get("top_features", ["?"])[0]
        peso = su.get("top_peso", 0)
        titulo_rf = "Por que o RF venceu" if su["rf_venceu"] else "Por que o RF não venceu"
        porque = (f"Combinou {top} ({peso:.0%} da importância) com o calendário." if su["rf_venceu"] else
                  f"Apoiou-se em {top} ({peso:.0%}) e teve poucas horas de treino; o "
                  f"{su['melhor_baseline']} já pega o ciclo diário sem treino.")
        lag = su.get("lag24")
        lag24 = (f"Precisa do dia anterior: coletamos 96 h para ele valer desde a P1. "
                 f"Ficou em {lag['posicao']}º de 8 em sucesso (MAE {num(lag['mae'])})." if lag else
                 "Precisa do dia anterior: coletamos 96 h para ele valer desde a P1.")
    else:
        titulo_rf = "Por que o RF venceu / não venceu"
        porque = "[feature principal e % da importância; poucas horas de treino ou combinação de features]"
        lag24 = "Precisa do dia anterior: coletamos 96 h para ele valer desde a P1. Ficou em [n]º de 8 (MAE [x])."
    cartao(s, 0.45, 3.05, 4.45, 1.15, titulo_rf, [porque], tam_titulo=12, tam_corpo=10)
    cartao(s, 5.1, 3.05, 4.45, 1.15, "Lag 24 h", [lag24], fundo=VERDE_CLARO, cor_titulo=VERDE,
           tam_titulo=12, tam_corpo=10)
    destaque(s, 0.45, 4.3, 9.1, "Observabilidade + previsão: escalar antes do pico. Próximo passo: mais dias de coleta", 12)
    if tem:
        su, er = r["sucesso"], r["erro"]
        fala = (f"Em sucesso, o melhor foi o {su['melhor_baseline']}, com MAE {num(su['mae_baseline'])}; o Random "
                f"Forest teve {num(su['mae_rf'])}. Em erro, {er['melhor_baseline']} com {num(er['mae_baseline'])} "
                f"contra {num(er['mae_rf'])} do Random Forest. {porque} Sobre o lag de 24 horas: ele só funciona "
                "se existir o dia anterior; por isso coletamos 96 horas, e ele já foi avaliado desde a primeira "
                "partição. Com mais dias de coleta, o modelo veria cada hora do dia várias vezes e poderia superar "
                "o baseline.")
    else:
        fala = ("Comparem o melhor baseline com o Random Forest nas duas séries, expliquem por quê e falem do lag "
                "de 24 horas: ele precisa do dia anterior, por isso coletamos 96 horas.")
    notas(s, f"Apresentador 5 (60 s): {fala} Obrigado, professor; ficamos à disposição para perguntas.")


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
        *[(lambda s, t=tipo, p=painel, n=nome, f=fala: slide_painel(s, t, p, n, f))
          for tipo in ("sucesso", "erro") for painel, nome, fala in PAINEIS[tipo]],
        lambda s: slide_coleta(s, resumo), slide_baselines, slide_particoes,
        *[(lambda s, se=serie, m=metrica: slide_resultado(s, resumo, se, m))
          for serie in ("sucesso", "erro") for metrica in ("MAE", "MSE")],
        lambda s: slide_execucao(s, resumo), slide_features,
        lambda s: slide_importancia(s, resumo, "sucesso"), lambda s: slide_importancia(s, resumo, "erro"),
        *[(lambda s, se=serie, f=func: f(s, resumo, se))
          for serie in ("sucesso", "erro") for func in (slide_previsoes, slide_evolucao)],
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
