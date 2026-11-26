# MecâniQA Automotive Tech — OAT 4 (API Django + Prometheus + Grafana)

Repositório base da **OAT 4 integrada** das disciplinas de **Computação em Nuvem** e **Modelos de Aprendizagem de Máquina**.

Este projeto fornece:
- Uma **API Django** já instrumentada com contadores do **Prometheus** (`/api/manutencoes/` e `/metrics`).
- **Dockerfiles** e `docker-compose.yml` para subir a **API Django**, o **Prometheus** e o **Grafana** (com o datasource Prometheus já conectado).
- Um **script gerador de tráfego** (`scripts/gerar_trafego.py`) e um **script de inicialização** (`run.sh`) que sobem o ambiente e disparam requisições contínuas gerando respostas aleatórias `2xx` (sucesso) e `4xx`/`5xx` (erro) com padrão sazonal diário.

> **Nota para os estudantes:** Os **dashboards no Grafana NÃO vêm prontos** — a criação dos dois dashboards (Requisições com Sucesso e Requisições com Erro) e a construção/avaliação dos modelos preditivos são parte do desafio da equipe.

---

## Estrutura do Repositório

```text
app-monitoring/
├── api/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── manage.py
│   └── mecaniqa_api/
│       ├── settings.py
│       ├── urls.py
│       ├── views.py          # Endpoints /api/manutencoes/, /metrics e /health/
│       └── wsgi.py
├── prometheus/
│   ├── Dockerfile
│   └── prometheus.yml        # Scrape da API Django a cada 5s
├── grafana/
│   ├── Dockerfile
│   └── provisioning/
│       └── datasources/
│           └── prometheus.yml
├── scripts/
│   └── gerar_trafego.py      # Gera tráfego contínuo (2xx, 4xx, 5xx)
├── docker-compose.yml
└── run.sh                    # Sobe a pilha e inicia o gerador de tráfego
```

---

## Pré-requisitos

- **Docker** e **Docker Compose** (`docker compose`)
- **Python 3** (para executar `scripts/gerar_trafego.py` — utiliza apenas biblioteca padrão, sem dependências extras)

---

## Como Executar

### Opção 1 — Script único (recomendado)
```bash
chmod +x run.sh
./run.sh
```

Esse comando:
1. Constrói e sobe os containers `mecaniqa-api`, `mecaniqa-prometheus` e `mecaniqa-grafana`;
2. Aguarda a API responder em `http://localhost:8000/health/`;
3. Inicia o script `scripts/gerar_trafego.py` para gerar a série temporal contínua de respostas `2xx`, `4xx` e `5xx`.

### Opção 2 — Passo a passo manual
```bash
# 1. Subir os serviços
docker compose up -d --build

# 2. Iniciar o gerador de tráfego (deixe rodando durante os 3 dias de coleta)
python3 scripts/gerar_trafego.py --url http://localhost:8000
```

Para parar os containers posteriormente:
```bash
docker compose down
```
*(Para apagar também os dados persistidos nos volumes do Prometheus e Grafana, use `docker compose down -v`.)*

---

## Endpoints e Serviços

| Serviço | URL | Credenciais / Detalhes |
| :--- | :--- | :--- |
| Endpoint monitorado | `http://localhost:8000/api/manutencoes/` | Retorna aleatoriamente `2xx`, `4xx` ou `5xx` |
| Métricas Prometheus | `http://localhost:8000/metrics` | Exposto no formato OpenMetrics/Prometheus |
| Healthcheck | `http://localhost:8000/health/` | Retorna `200 OK` |
| Prometheus UI | `http://localhost:9090` | Retenção configurada para `15d` |
| Grafana UI | `http://localhost:3000` | Usuário: `admin` \| Senha: `admin` |

---

## Métricas Expostas no Prometheus

| Métrica | Tipo | Labels | Descrição |
| :--- | :--- | :--- | :--- |
| `mecaniqa_api_requests_success_total` | Counter | `endpoint`, `status_code` | Total acumulado de requisições com sucesso (`2xx`) |
| `mecaniqa_api_requests_error_total` | Counter | `endpoint`, `status_code`, `error_class` | Total acumulado de requisições com erro (`4xx` e `5xx`) |
| `mecaniqa_api_requests_total` | Counter | `endpoint`, `status_code`, `status_class` | Total acumulado geral por classe de status (`2xx`, `4xx`, `5xx`) |

### Exemplos de consultas PromQL para os Dashboards no Grafana
- **Requisições com sucesso por hora:**
  ```promql
  sum(increase(mecaniqa_api_requests_success_total[1h]))
  ```
- **Requisições com erro por hora:**
  ```promql
  sum(increase(mecaniqa_api_requests_error_total[1h]))
  ```
- **Taxa de sucesso por minuto (tempo real):**
  ```promql
  sum(rate(mecaniqa_api_requests_success_total[5m])) * 60
  ```
- **Taxa de erro por minuto (tempo real):**
  ```promql
  sum(rate(mecaniqa_api_requests_error_total[5m])) * 60
  ```

---

## Exemplo de Coleta dos 3 Dias via API do Prometheus (Python)

Os estudantes podem extrair a série temporal horária diretamente da API HTTP do Prometheus (`/api/v1/query_range`):

```python
import time
import urllib.parse
import urllib.request
import json
import pandas as pd

PROM_URL = "http://localhost:9090/api/v1/query_range"
end = int(time.time())
start = end - 3 * 24 * 3600  # últimos 3 dias

def fetch_series(promql: str, col_name: str) -> pd.DataFrame:
    params = urllib.parse.urlencode({
        "query": promql,
        "start": start,
        "end": end,
        "step": "1h",
    })
    with urllib.request.urlopen(f"{PROM_URL}?{params}") as resp:
        data = json.loads(resp.read().decode())
    values = data["data"]["result"][0]["values"]
    df = pd.DataFrame(values, columns=["timestamp", col_name])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
    df[col_name] = df[col_name].astype(float)
    return df

df_sucesso = fetch_series("sum(increase(mecaniqa_api_requests_success_total[1h]))", "sucesso")
df_erro = fetch_series("sum(increase(mecaniqa_api_requests_error_total[1h]))", "erro")
df = pd.merge(df_sucesso, df_erro, on="timestamp", how="outer").sort_values("timestamp")
df.to_csv("serie_temporal_3dias.csv", index=False)
```
