# Evidências — MecaniQA (Equipe Macapá)

Capturas geradas em 11/11/2026 no Docker Desktop (Kubernetes `docker-desktop`, modo kind, v1.36.1).
Prints de terminal mostram a saída real dos comandos indicados no topo de cada bloco.

## OAT 1 — Docker, Docker Compose, Kubernetes e Terraform (`oat1/`)

| Arquivo | O que comprova |
| --- | --- |
| `01-compose-ps.png` | Três serviços do Compose `healthy`, volumes nomeados e rede dedicada |
| `02-compose-endpoints.png` | `GET /` e `GET /health` da API Java (HTTP 200, `UP`) |
| `03-smoke-test.png` | `scripts/smoke-test.ps1` aprovado (200, 404 e 405) |
| `04-persistencia-restart.png` | Dado gravado no Redis permanece após `docker compose restart db cache` |
| `05-k8s-pods-pvc.png` | Quatro Pods `1/1 Running` (2 API, MySQL, Redis), Deployments, Services e dois PVCs `Bound` |
| `06-k8s-health.png` | API no Kubernetes via port-forward (8081) e smoke test aprovado |
| `07-k8s-auto-healing.png` | Pod da API removido e recriado automaticamente pelo Deployment (2/2) |
| `08-terraform-validate.png` | `terraform init`, `fmt -check` e `validate` com sucesso |
| `09-terraform-plan.png` | `terraform plan` contra o cluster: 10 recursos equivalentes ao manifesto |

## OAT 2 — Sessão 07/10: simulador IoT e Prometheus (`oat2-07-10/`)

| Arquivo | O que comprova |
| --- | --- |
| `01-pods-servicos.png` | Pods, Services e PVC do simulador e do Prometheus; StorageClass padrão |
| `02-test-oat2.png` | `scripts/test-oat2.ps1` aprovado: saúde, leitura válida, rejeição 422 e métricas |
| `03-metricas-simulador.png` | Endpoint `/metrics` com contadores de sucesso/erro e última leitura dos sensores |
| `04-prometheus-targets.png` | Targets `kubelet-cadvisor`, `mecaniqa-iot` e `prometheus` em `UP` |
| `05-prometheus-leituras-por-resultado.png` | PromQL: taxa de leituras por resultado (sucesso × erro) |
| `06-prometheus-ultima-leitura-sensores.png` | PromQL: último valor por tipo de sensor |

## OAT 2 — Sessão 14/10: Grafana e dashboards (`oat2-14-10/`)

| Arquivo | O que comprova |
| --- | --- |
| `01-grafana-datasource-prometheus.png` | Datasource provisionado e teste de conexão bem-sucedido |
| `02-grafana-lista-dashboards.png` | Quatro dashboards provisionados na pasta MecaniQA |
| `03` a `06` | Dashboards de CPU, memória, erros e sucessos nas últimas 3 horas (inclui os picos do teste) |

## OAT 2 — Sessão 21/10: HPA, alarmes e teste de estresse (raiz desta pasta)

| Arquivo | O que comprova |
| --- | --- |
| `01-grafana-alertas-firing.png` | As quatro regras de alerta em **Firing** durante o teste de estresse |
| `02-dashboard-cpu.png` | CPU dos Pods no pico, com as novas réplicas surgindo |
| `03-dashboard-erros.png` | Cerca de 20% de leituras rejeitadas por Pod durante a carga |
| `04-dashboard-sucessos.png` | Pico de leituras processadas com sucesso por Pod |
| `05-dashboard-memoria.png` | Memória dos Pods durante a carga |
| `06-hpa-escalonamento.png` | HPA em 5/5 réplicas, `kubectl top` e eventos `SuccessfulRescale` |

### Logs do teste de estresse (`oat2-21-10-logs/`)

Saída real dos comandos, capturada no pico da carga.

| Arquivo | O que comprova |
| --- | --- |
| `hpa-describe.txt` | `kubectl describe hpa`: CPU em 239% contra alvo de 60%, 5/5 réplicas e eventos `SuccessfulRescale` (subida e descida) |
| `hpa.yaml` | Estado do objeto HPA no cluster durante o teste |
| `pods-scaled.txt` | Cinco Pods do simulador `1/1 Running`, sem reinícios |
| `top-pods.txt` | `kubectl top pods`: consumo de CPU e memória por Pod durante a carga |
| `k8s-events.txt` | Eventos do namespace, incluindo os reescalonamentos do HPA |
| `iot-metrics-snapshot.txt` | Endpoint `/metrics` do simulador durante a sessão de teste (contadores de sucesso e erro) |

Teste de estresse: gerador executado dentro do cluster (Job) contra o Service `mecaniqa-iot`,
60 threads, 20% de payloads inválidos. Rodada de 180 s: 262.544 requisições (~1.440 req/s),
209.525 sucessos, 52.709 rejeições 422, sem reinícios nem `OOMKilled`. O HPA escalou de 1 para
5 réplicas em cerca de 45 s e reduziu após o fim da carga.
