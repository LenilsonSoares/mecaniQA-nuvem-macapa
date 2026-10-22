#!/usr/bin/env python3
"""Script automatizado para capturar screenshots do Grafana e evidências do teste."""

import argparse
import os
import time
from playwright.sync_api import sync_playwright


def capture_grafana_evidence(base_url: str, user: str, password: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    print("=== Captura Automatizada de Evidências no Grafana ===")
    print(f"URL: {base_url} | Destino: {output_dir}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        try:
            print("[1/5] Realizando login no Grafana...")
            page.goto(f"{base_url}/login", timeout=15000)
            page.fill("input[name='user']", user)
            page.fill("input[name='password']", password)
            page.click("button[type='submit']")
            page.wait_for_url(f"{base_url}/**", timeout=15000)
            time.sleep(2)
        except Exception as e:
            print(f"Aviso no login (tentando prosseguir caso anônimo ativo): {e}")

        # 1. Screenshot da tela de Alertas (Alert Rules)
        try:
            print("[2/5] Capturando tela de Alarmes (Alerting)...")
            page.goto(f"{base_url}/alerting/list", timeout=15000)
            time.sleep(4)
            alert_path = os.path.join(output_dir, "01-grafana-alertas-firing.png")
            page.screenshot(path=alert_path, full_page=True)
            print(f"  Salvo: {alert_path}")
        except Exception as e:
            print(f"  Erro ao capturar tela de alertas: {e}")

        # 2. Screenshot do Dashboard de CPU
        try:
            print("[3/5] Capturando Dashboard de CPU dos Pods...")
            page.goto(f"{base_url}/d/mecaniqa-cpu", timeout=15000)
            time.sleep(4)
            cpu_path = os.path.join(output_dir, "02-dashboard-cpu.png")
            page.screenshot(path=cpu_path, full_page=True)
            print(f"  Salvo: {cpu_path}")
        except Exception as e:
            print(f"  Tentando buscar dashboard de CPU: {e}")

        # 3. Screenshot do Dashboard de Erros e Sucessos
        try:
            print("[4/5] Capturando Dashboard de Erros...")
            page.goto(f"{base_url}/d/mecaniqa-erros", timeout=15000)
            time.sleep(4)
            erros_path = os.path.join(output_dir, "03-dashboard-erros.png")
            page.screenshot(path=erros_path, full_page=True)
            print(f"  Salvo: {erros_path}")
        except Exception as e:
            print(f"  Erro ao capturar dashboard de erros: {e}")

        try:
            print("[5/5] Capturando Dashboard de Sucessos...")
            page.goto(f"{base_url}/d/mecaniqa-sucessos", timeout=15000)
            time.sleep(4)
            sucessos_path = os.path.join(output_dir, "04-dashboard-sucessos.png")
            page.screenshot(path=sucessos_path, full_page=True)
            print(f"  Salvo: {sucessos_path}")
        except Exception as e:
            print(f"  Erro ao capturar dashboard de sucessos: {e}")

        browser.close()
        print("\nCaptura concluída com sucesso!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Grafana Evidence Screenshot Tool")
    parser.add_argument("--url", default="http://127.0.0.1:3000", help="URL do Grafana")
    parser.add_argument("--user", default="admin", help="Usuário admin")
    parser.add_argument("--password", default="admin", help="Senha do admin")
    parser.add_argument("--out", default="docs/evidencias", help="Diretório de saída")
    args = parser.parse_args()

    capture_grafana_evidence(args.url.rstrip("/"), args.user, args.password, args.out)
