#!/usr/bin/env python3
"""Gerador de estresse HTTP concorrente para o MecaniQA IoT."""

import argparse
import json
import random
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def send_reading(url: str, is_error: bool) -> tuple[int, bool]:
    if is_error:
        payload = {"sensor_type": "battery_voltage", "value": -10.0}
    else:
        sensor = random.choice(["engine_temperature", "battery_voltage"])
        val = (
            random.uniform(70.0, 105.0)
            if sensor == "engine_temperature"
            else random.uniform(11.8, 14.5)
        )
        payload = {"sensor_type": sensor, "value": round(val, 2)}

    data = json.dumps(payload).encode("utf-8")
    req = Request(
        f"{url}/readings",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(req, timeout=3) as resp:
            return resp.status, True
    except HTTPError as e:
        # Erro 422 é a rejeição esperada para leituras inválidas
        return e.code, False
    except (URLError, TimeoutError, Exception):
        return 0, False


def run_stress(
    target_url: str, duration_sec: int, concurrency: int, error_ratio: float
):
    print("=== Iniciando Teste de Estresse IoT ===")
    print(f"Alvo: {target_url}/readings")
    print(
        f"Duração: {duration_sec}s | Concorrência: {concurrency} threads | Taxa de Erro: {int(error_ratio * 100)}%"
    )

    start_time = time.time()
    end_time = start_time + duration_sec
    total_requests = 0
    total_success = 0
    total_error_expected = 0
    connection_failures = 0

    def worker_loop():
        nonlocal \
            total_requests, \
            total_success, \
            total_error_expected, \
            connection_failures
        while time.time() < end_time:
            is_err = random.random() < error_ratio
            code, ok = send_reading(target_url, is_err)
            total_requests += 1
            if ok and code == 200:
                total_success += 1
            elif code == 422:
                total_error_expected += 1
            else:
                connection_failures += 1

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(worker_loop) for _ in range(concurrency)]
        while any(not f.done() for f in futures):
            elapsed = time.time() - start_time
            rps = total_requests / elapsed if elapsed > 0 else 0
            print(
                f"\rTempo: {int(elapsed)}s/{duration_sec}s | Req: {total_requests} (200 OK: {total_success}, 422 Erro: {total_error_expected}, Falhas: {connection_failures}) | RPS: {rps:.1f}",
                end="",
                flush=True,
            )
            time.sleep(1)

    elapsed = time.time() - start_time
    rps = total_requests / elapsed if elapsed > 0 else 0
    print("\n\n=== Teste de Estresse Concluído ===")
    print(f"Tempo total: {elapsed:.2f}s")
    print(f"Requisições totais: {total_requests}")
    print(f"Sucessos (200 OK): {total_success}")
    print(f"Erros de Ingestão (422 Rejeitados): {total_error_expected}")
    print(f"Falhas de conexão: {connection_failures}")
    print(f"Throughput médio: {rps:.2f} req/s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MecaniQA IoT Load Generator")
    parser.add_argument(
        "--url", default="http://127.0.0.1:8000", help="URL base da API IoT"
    )
    parser.add_argument("--duration", type=int, default=60, help="Duração em segundos")
    parser.add_argument(
        "--concurrency", type=int, default=30, help="Número de workers simultâneos"
    )
    parser.add_argument(
        "--error-ratio",
        type=float,
        default=0.15,
        help="Proporção de leituras inválidas",
    )
    args = parser.parse_args()

    run_stress(args.url.rstrip("/"), args.duration, args.concurrency, args.error_ratio)
