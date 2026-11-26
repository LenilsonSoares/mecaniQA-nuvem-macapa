#!/usr/bin/env python3
"""
Gerador de tráfego contínuo para a API Django da MecâniQA (OAT 4).

Envia requisições ao endpoint /api/manutencoes/ com taxa de requisições e
probabilidade de erro (4xx/5xx) moduladas por um padrão sazonal diário
somado a ruído estocástico, produzindo uma série temporal realista ao longo
dos 3 dias de coleta.

Não requer bibliotecas externas (usa apenas a biblioteca padrão do Python).
"""

import argparse
import math
import random
import signal
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime


RUNNING = True


def handle_signal(signum, frame):
    global RUNNING
    RUNNING = False
    print("\n[INFO] Encerrando gerador de tráfego...")


def compute_hourly_profile(now: datetime) -> tuple[float, float]:
    """
    Calcula o intervalo médio entre requisições (segundos) e a taxa de erro
    esperada conforme a hora do dia, simulando o ritmo de oficinas mecânicas:
      - Horário comercial (08h-18h): maior volume de requisições, com picos ~10h e ~15h.
      - Madrugada (00h-06h): baixo volume de requisições.
      - Taxa de erro varia suavemente com a carga + ruído aleatório e eventuais surtos.
    """
    hour_float = now.hour + now.minute / 60.0

    # Componente sazonal diária (pico no meio do dia, vale na madrugada)
    daily_wave = 0.5 * (1.0 + math.sin(2.0 * math.pi * (hour_float - 7.0) / 24.0))

    # Dois picos comerciais adicionais: manhã (~10h) e tarde (~15h)
    morning_peak = math.exp(-0.5 * ((hour_float - 10.0) / 2.0) ** 2)
    afternoon_peak = math.exp(-0.5 * ((hour_float - 15.0) / 2.2) ** 2)

    # Intensidade de tráfego (requisições por segundo)
    intensity_rps = 0.3 + 1.8 * daily_wave + 1.2 * morning_peak + 1.0 * afternoon_peak
    intensity_rps *= random.uniform(0.75, 1.25)
    sleep_seconds = max(0.08, random.expovariate(intensity_rps))

    # Taxa de erro base entre ~10% e ~35% conforme carga + chance de surto
    error_rate = 0.10 + 0.18 * daily_wave + 0.08 * afternoon_peak + random.uniform(-0.04, 0.04)

    # Surtos esporádicos de erro (2% de chance por requisição)
    if random.random() < 0.02:
        error_rate = min(0.85, error_rate + 0.40)

    error_rate = max(0.05, min(0.90, error_rate))
    return sleep_seconds, error_rate


def send_request(base_url: str, error_rate: float, timeout: float = 5.0) -> int:
    url = f"{base_url.rstrip('/')}/api/manutencoes/?error_rate={error_rate:.3f}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
            return resp.status
    except urllib.error.HTTPError as exc:
        # 4xx e 5xx são esperados como parte da simulação
        return exc.code
    except Exception as exc:
        print(f"[AVISO] Falha de conexão com a API ({url}): {exc}", file=sys.stderr)
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="Gera tráfego contínuo (2xx, 4xx, 5xx) para a API MecâniQA."
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="URL base da API Django (padrão: http://localhost:8000)",
    )
    parser.add_argument(
        "--log-every",
        type=int,
        default=20,
        help="Exibir resumo no terminal a cada N requisições (padrão: 20)",
    )
    args = parser.parse_args()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    counts = {"2xx": 0, "4xx": 0, "5xx": 0, "conn_err": 0}
    total = 0

    print(f"[INFO] Iniciando geração de tráfego contra {args.url}/api/manutencoes/")
    print("[INFO] Pressione Ctrl+C para interromper.\n")

    while RUNNING:
        now = datetime.now()
        sleep_s, error_rate = compute_hourly_profile(now)
        status = send_request(args.url, error_rate)
        total += 1

        if 200 <= status < 300:
            counts["2xx"] += 1
        elif 400 <= status < 500:
            counts["4xx"] += 1
        elif 500 <= status < 600:
            counts["5xx"] += 1
        else:
            counts["conn_err"] += 1

        if total % args.log_every == 0:
            ts = now.strftime("%Y-%m-%d %H:%M:%S")
            print(
                f"[{ts}] Total={total} | 2xx={counts['2xx']} | "
                f"4xx={counts['4xx']} | 5xx={counts['5xx']} | "
                f"FalhaConexao={counts['conn_err']} | error_rate_atual={error_rate:.2f}",
                flush=True,
            )

        time.sleep(sleep_s)

    print(
        f"[RESUMO FINAL] Total={total} | 2xx={counts['2xx']} | "
        f"4xx={counts['4xx']} | 5xx={counts['5xx']} | FalhaConexao={counts['conn_err']}"
    )


if __name__ == "__main__":
    main()
