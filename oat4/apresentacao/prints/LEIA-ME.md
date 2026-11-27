# Prints da apresentação (OAT 4)

O professor valoriza **imagens grandes mostrando o que é real**. Salve aqui os prints com
**exatamente** estes nomes (`.png` ou `.jpg`) e rode `py apresentacao/gerar_slides.py --pdf`
na pasta `oat4/`. Cada um entra sozinho, grande, no slide certo.

| Arquivo | Slide | O que capturar |
| --- | --- | --- |
| `ambiente_docker.png` | 5 — Ambiente | Terminal com `docker compose ps` mostrando os 4 serviços **Up** (api, prometheus, grafana, gerador) |
| `ambiente_targets.png` | 5 — Ambiente | http://localhost:9090/targets com `mecaniqa-django-api` **UP** |
| `dashboard_sucesso.png` | 6 — Dashboard 1 | Grafana › MecaniQA › *Requisições com Sucesso*, "Last 3 days", **data e hora visíveis** |
| `dashboard_erro.png` | 7 — Dashboard 2 | Grafana › MecaniQA › *Requisições com Erro*, "Last 3 days", **data e hora visíveis** |

Dicas para ficarem nítidos:
- Navegador em tela cheia (F11), zoom 100%; recorte só a área útil (sem barra de tarefas).
- Dashboards no **mesmo tema** (claro ou escuro) e tirados **no fim da coleta**, com os 3 dias inteiros.
- Terminal com fonte grande (Ctrl + roda do mouse) antes do print.
- Os gráficos e tabelas dos outros slides vêm de `oat4/resultados/` (gerados por `analise/analise_oat4.py`).
