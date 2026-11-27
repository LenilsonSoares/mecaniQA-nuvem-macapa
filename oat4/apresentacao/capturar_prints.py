"""Captura os prints da OAT 4 em alta resolução, sempre no mesmo padrão visual.

Gera em apresentacao/prints/ (os nomes que o gerador de slides espera):
    ambiente_docker.png       terminal com `docker compose ps` (os 4 serviços)
    ambiente_targets.png      Prometheus › Targets com a API em UP
    dashboard_sucesso.png     Grafana, dashboard de sucesso, período da coleta
    dashboard_erro.png        Grafana, dashboard de erro, período da coleta
    coleta_grafana_3dias.png  painéis "por hora" de sucesso e erro, um sobre o outro

Os dashboards são capturados em modo quiosque (sem menus do Grafana), com escala 2x
(nítido no projetor) e uma faixa de legenda com o período e a hora da captura.

Uso (na pasta oat4, com a pilha rodando):
    .venv/Scripts/python.exe apresentacao/capturar_prints.py --inicio "2026-11-27 17:00"
    .venv/Scripts/python.exe apresentacao/capturar_prints.py --inicio "2026-11-27 17:00" --tema dark
Sem --inicio, usa as últimas 72 horas.
"""

import argparse
import base64
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

PASTA_OAT4 = Path(__file__).resolve().parents[1]
PILHA = PASTA_OAT4 / "app-monitoring"
SAIDA = PASTA_OAT4 / "apresentacao" / "prints"
GRAFANA = "http://localhost:3000"
PROMETHEUS = "http://localhost:9090"
CREDENCIAIS = base64.b64encode(b"admin:admin").decode()
DASHBOARDS = {"sucesso": "mecaniqa-oat4-sucesso", "erro": "mecaniqa-oat4-erro"}
PAINEL_POR_HORA = 5  # id do painel "Requisições ... por hora" nos dois dashboards
ESCALA = 2

FONTES = Path("C:/Windows/Fonts")


def fonte(nome, tamanho):
    """Fonte do Windows; se não existir (Linux/Mac), usa a padrão do Pillow."""
    try:
        return ImageFont.truetype(str(FONTES / nome), tamanho)
    except OSError:
        return ImageFont.load_default(size=tamanho)


def legenda(imagem: Path, texto: str, tema: str):
    """Acrescenta uma faixa fina embaixo do print com período e hora da captura."""
    im = Image.open(imagem).convert("RGB")
    altura = 26 * ESCALA
    fundo, cor = ((24, 27, 31), (204, 204, 220)) if tema == "dark" else ((244, 245, 245), (70, 70, 70))
    nova = Image.new("RGB", (im.width, im.height + altura), fundo)
    nova.paste(im, (0, 0))
    ImageDraw.Draw(nova).text((14 * ESCALA, im.height + 6 * ESCALA), texto, fill=cor,
                              font=fonte("segoeui.ttf", 13 * ESCALA))
    nova.save(imagem)


def capturar(pagina, url, arquivo, largura, altura, espera_ms=5000):
    pagina.set_viewport_size({"width": largura, "height": altura})
    pagina.goto(url, wait_until="networkidle")
    pagina.wait_for_timeout(espera_ms)  # painéis terminam de desenhar após a resposta
    pagina.screenshot(path=str(arquivo))
    print("  ✓", arquivo.name)


def print_terminal(arquivo: Path):
    """Desenha a saída real de `docker compose ps` numa janela de terminal."""
    comando = ["docker", "compose", "ps", "--format", "table {{.Service}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"]
    saida = subprocess.run(comando, cwd=PILHA, capture_output=True, text=True, check=True).stdout.rstrip()
    momento = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    linhas = [("prompt", f"PS {PILHA}> docker compose ps")] + [("saida", l) for l in saida.splitlines()]
    linhas += [("saida", ""), ("prompt", f"PS {PILHA}> Get-Date"), ("saida", momento)]

    mono = fonte("consola.ttf", 17 * ESCALA)
    altura_linha = 26 * ESCALA
    largura = max(1500 * ESCALA // 2 * 2, max(int(mono.getlength(t)) for _, t in linhas) + 60 * ESCALA)
    barra = 40 * ESCALA
    altura = barra + 24 * ESCALA + altura_linha * len(linhas) + 20 * ESCALA
    im = Image.new("RGB", (largura, altura), (12, 12, 12))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, largura, barra], fill=(43, 43, 43))
    d.text((16 * ESCALA, 10 * ESCALA), "Windows PowerShell — MecâniQA OAT 4", fill=(230, 230, 230),
           font=fonte("segoeui.ttf", 14 * ESCALA))
    for i, cor in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        x = largura - (90 - i * 26) * ESCALA
        d.ellipse([x, 13 * ESCALA, x + 14 * ESCALA, 27 * ESCALA], fill=cor)
    y = barra + 16 * ESCALA
    for tipo, texto in linhas:
        cor = (97, 214, 214) if tipo == "prompt" else (204, 204, 204)
        if tipo == "saida" and " Up " in f" {texto} ":
            cor = (120, 220, 120)
        d.text((20 * ESCALA, y), texto, fill=cor, font=mono)
        y += altura_linha
    im.save(arquivo)
    print("  ✓", arquivo.name)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--inicio", help='início do período nos dashboards (ex.: "2026-11-27 17:00")')
    parser.add_argument("--fim", help="fim do período (padrão: agora)")
    parser.add_argument("--tema", choices=["light", "dark"], default="light")
    args = parser.parse_args()

    fim = datetime.fromisoformat(args.fim) if args.fim else datetime.now()
    inicio = datetime.fromisoformat(args.inicio) if args.inicio else fim - timedelta(hours=72)
    de, ate = int(inicio.timestamp() * 1000), int(fim.timestamp() * 1000)
    periodo = f"{inicio:%d/%m/%Y %H:%M} → {fim:%d/%m/%Y %H:%M} (UTC-3)"
    capturado = f"capturado em {datetime.now():%d/%m/%Y %H:%M}"
    SAIDA.mkdir(parents=True, exist_ok=True)
    print(f"Período: {periodo}")

    print_terminal(SAIDA / "ambiente_docker.png")
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        contexto = navegador.new_context(device_scale_factor=ESCALA, locale="pt-BR", timezone_id="America/Bahia",
                                         extra_http_headers={"Authorization": f"Basic {CREDENCIAIS}"})
        pagina = contexto.new_page()

        alvo = SAIDA / "ambiente_targets.png"
        capturar(pagina, f"{PROMETHEUS}/targets", alvo, 1500, 300, espera_ms=2500)
        legenda(alvo, f"Prometheus › Status › Targets · {capturado}", "light")

        for nome, uid in DASHBOARDS.items():
            arquivo = SAIDA / f"dashboard_{nome}.png"
            url = f"{GRAFANA}/d/{uid}?orgId=1&from={de}&to={ate}&theme={args.tema}&kiosk"
            capturar(pagina, url, arquivo, 1600, 900)
            legenda(arquivo, f"Grafana › MecâniQA › Requisições com {'Sucesso (2xx)' if nome == 'sucesso' else 'Erro (4xx/5xx)'}"
                             f" · {periodo} · {capturado}", args.tema)

        # Coleta: os dois painéis "por hora", empilhados numa imagem só.
        partes = []
        for nome, uid in DASHBOARDS.items():
            parte = SAIDA / f"_painel_{nome}.png"
            url = f"{GRAFANA}/d-solo/{uid}?orgId=1&panelId={PAINEL_POR_HORA}&from={de}&to={ate}&theme={args.tema}"
            capturar(pagina, url, parte, 1600, 380)
            partes.append(Image.open(parte).convert("RGB"))
        navegador.close()

    coleta = SAIDA / "coleta_grafana_3dias.png"
    junta = Image.new("RGB", (partes[0].width, sum(i.height for i in partes)), (255, 255, 255))
    y = 0
    for parte in partes:
        junta.paste(parte, (0, y))
        y += parte.height
    junta.save(coleta)
    for temporario in SAIDA.glob("_painel_*.png"):
        temporario.unlink()
    legenda(coleta, f"Grafana › MecâniQA · sucesso e erro por hora · {periodo} · {capturado}", args.tema)
    print("  ✓", coleta.name)
    print(f"Prints salvos em {SAIDA}. Rode apresentacao/gerar_slides.py --pdf para colocá-los nos slides.")


if __name__ == "__main__":
    main()
