# Prints da apresentação (OAT 4)

Salve aqui os prints com **exatamente** estes nomes (`.png` ou `.jpg`) e rode
`py apresentacao/gerar_slides.py --pdf` na pasta `oat4/`. Eles entram sozinhos no slide certo.

| Arquivo | Slide | O que capturar |
| --- | --- | --- |
| `ambiente.png` | 5 — Ambiente em funcionamento | Terminal com `docker compose ps` (4 serviços *Up*) **e** a página http://localhost:9090/targets com `mecaniqa-django-api` **UP** (pode juntar os dois numa imagem) |
| `dashboard_sucesso.png` | 6 — Dashboard 1 | Grafana › MecaniQA › *Requisições com Sucesso*, intervalo "Last 3 days", **com data e hora visíveis** |
| `dashboard_erro.png` | 7 — Dashboard 2 | Grafana › MecaniQA › *Requisições com Erro*, intervalo "Last 3 days", **com data e hora visíveis** |

Dicas:
- Use a tela cheia do navegador (F11) e o modo claro ou escuro do Grafana, mas o mesmo nos dois dashboards.
- Tire os prints **no fim da coleta**, quando os 3 dias aparecem inteiros nos gráficos.
- Os gráficos e as tabelas dos outros slides vêm de `oat4/resultados/` (gerados por `analise/analise_oat4.py`).
