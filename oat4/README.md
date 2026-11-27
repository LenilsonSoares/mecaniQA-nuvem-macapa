# OAT 4 — Observabilidade em Nuvem e Predição de Requisições

Atividade integrada de **Computação em Nuvem** e **Modelos de Aprendizado de Máquina**
(Equipe Macapá). Sobe a API Django do professor com Prometheus e Grafana, coleta
3 dias de telemetria real e prevê as requisições com sucesso (2xx) e com erro (4xx/5xx).

> O código desta OAT **não é avaliado**: só conta o que aparecer na apresentação.
> Por isso, todo passo abaixo termina em uma evidência (print, tabela ou gráfico).

## Estrutura

```text
oat4/
├── app-monitoring/        # base fornecida pelo professor (github.com/mecaniQA/app-monitoring)
│   ├── api/               # API Django com contadores Prometheus (sem alterações)
│   ├── prometheus/        # scrape da API a cada 5 s (sem alterações)
│   ├── grafana/           # + 2 dashboards provisionados (sucesso e erro)
│   ├── scripts/           # gerador de tráfego do professor (sem alterações)
│   └── docker-compose.yml # + serviço "gerador" com reinício automático
├── coleta/coletar_prometheus.py   # exporta a série horária do Prometheus para CSV
├── analise/analise_oat4.py        # 7 baselines × 4 partições (MAE/MSE) + Random Forest
├── apresentacao/          # gerador dos slides no modelo da disciplina + prints/
├── dados/                 # serie_horaria.csv (gerado pela coleta)
├── resultados/            # tabelas e gráficos para os slides (gerados pela análise)
└── requirements.txt       # dependências da análise
```

Alterações em relação ao repositório do professor:
1. **Gerador de tráfego como container** (`gerador` no `docker-compose.yml`, `restart: unless-stopped`):
   volta sozinho depois de queda de energia ou reinício do Docker, sem deixar terminal aberto.
2. **Fuso UTC-3 no gerador**: o padrão diário (picos ~10 h e ~15 h) segue o horário de Brasília.
3. **Dashboards provisionados**: o Grafana já sobe com *Requisições com Sucesso* e *Requisições com Erro*.

## 1. Subir o ambiente (máquina que ficará ligada)

Pré-requisito: Docker Desktop aberto. Desative a suspensão do computador.

```powershell
cd oat4/app-monitoring
docker compose up -d --build
docker compose ps          # 4 serviços: api, prometheus, grafana, gerador
```

| Serviço | Endereço | O que conferir |
| --- | --- | --- |
| API | http://localhost:8000/health/ | `{"status": "ok"}` |
| Métricas | http://localhost:8000/metrics | contadores `mecaniqa_api_requests_*` |
| Prometheus | http://localhost:9090/targets | alvo `mecaniqa-django-api` **UP** |
| Grafana | http://localhost:3000 (admin/admin) | pasta **MecaniQA** com os 2 dashboards |

Logs do gerador: `docker compose logs -f gerador`.

## 2. Coletar (mínimo 96 h)

Deixe rodando **pelo menos 4 dias**: o primeiro dia é histórico (o lag de 24 h e a média
de 24 h precisam dele) e os **3 últimos dias são a janela avaliada**. Anote no grupo o
horário de início e qualquer queda de energia.

Os prints saem prontos, em alta resolução e com data e hora na legenda (veja a seção 4).

Ao final:

```powershell
cd oat4/coleta
py coletar_prometheus.py            # gera ../dados/serie_horaria.csv (96 h até a última hora cheia)
```

## 3. Analisar

```powershell
cd oat4
py -m pip install -r requirements.txt
py apresentacao/capturar_prints.py --analise   # roda analise/analise_oat4.py e salva o print do terminal
```

(`py analise/analise_oat4.py` roda a mesma análise sem gerar o print.)

Saídas em `resultados/`:

| Arquivo | Slide |
| --- | --- |
| `01_serie_coletada.png` | coleta dos 3 dias |
| `tabela_mae_*.csv`, `tabela_mse_*.csv`, `02_heatmap_*.png` | 7 baselines × 4 partições |
| `03_previsoes_*.png` | real × melhor baseline × Random Forest |
| `04_evolucao_mae_*.png` | evolução do erro conforme cresce o histórico |
| `05_importancia_features_*.png` | feature engineering |
| `metricas_todas.csv`, `previsoes_*.csv` | números completos |

## 4. Slides

A apresentação segue o **Modelo de Apresentação da disciplina** (base: `docs/apresentacoes/mecaniQA_oat2_macapa.pptx`)
e já tem os 18 slides, com roteiro de fala nas anotações de cada slide.

1. No fim da coleta, **com a pilha ainda rodando**, gere os prints (Docker, Prometheus e os 2 dashboards):
   ```powershell
   py -m pip install -r requirements.txt
   py -m playwright install chromium
   py apresentacao/capturar_prints.py --inicio "2026-11-27 17:00"   # início das 72 h avaliadas
   ```
   Eles vão para `apresentacao/prints/` com os nomes do [LEIA-ME](apresentacao/prints/LEIA-ME.md).
2. Rode, na pasta `oat4/`:
   ```powershell
   py apresentacao/gerar_slides.py --pdf
   ```
   Gráficos, tabelas de MAE/MSE e números (período, totais, melhor modelo) entram sozinhos.
3. Abra `apresentacao/mecaniQA_oat4_macapa.pptx` no **Google Slides** (fonte Poppins do modelo), revise e baixe o PDF
   como **`mecaniQA_oat4_macapa.pdf`**. Envie nos **dois** Blackboards (ML e Nuvem).

Enquanto não houver coleta, o PDF sai como `mecaniQA_oat4_macapa_RASCUNHO.pdf`, com espaços marcados "⟶ INSERIR".

## Protocolo de avaliação

- **Baselines:** lag de 1, 3, 12 e 24 h; média móvel simples de 3, 12 e 24 h
  (sempre com `shift(1)`: a hora prevista nunca entra na média).
- **Partições:** cumulativas sobre as últimas 72 h — P1 = 18 h, P2 = 36 h, P3 = 54 h, P4 = 72 h.
  MAE e MSE calculados separadamente para sucesso e erro.
- **Random Forest (walk-forward):** para cada hora da janela, treina só com as horas anteriores
  e prevê a hora seguinte; os erros são agrupados nas mesmas partições dos baselines.
- **Features:** hora do dia, período do dia, dia da semana, lags (1, 2, 3, 24 h), médias e
  desvios móveis (3, 6, 12, 24 h), tendência entre horas consecutivas e a outra série defasada.

## Pontuação (barema da OAT 4)

| Critério | Pontos | Evidência |
| --- | ---: | --- |
| Ambiente Prometheus-Grafana | 1,0 | `docker compose ps` + alvo UP |
| Dashboards (sucesso e erro) | 1,0 | prints dos 2 dashboards |
| Coleta de 3 dias | 1,0 | `01_serie_coletada.png` + período |
| 7 baselines | 1,5 | tabelas e heatmaps |
| Partições MAE/MSE | 1,5 | tabelas por partição |
| Feature engineering | 1,0 | importância das features + justificativa |
| Modelo de ML e comparação | 1,0 | `03_previsoes_*`, `04_evolucao_*` |
| Apresentação e participação | 1,0 | todos os 5 falam |
| Material (fontes, imagens, agenda, contexto) | 1,0 | modelo da disciplina |
