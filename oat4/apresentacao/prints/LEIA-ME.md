# Prints da apresentação (OAT 4)

O professor valoriza **imagens grandes mostrando o que é real**. Os prints são gerados
automaticamente, em alta resolução (2x) e sempre no mesmo padrão, por:

```powershell
cd oat4
py apresentacao/capturar_prints.py --inicio "2026-11-27 17:00"   # início das 72 h avaliadas
py apresentacao/gerar_slides.py --pdf                            # coloca os prints nos slides
```

Rode **no fim da coleta, com a pilha ainda no ar** (`docker compose ps` com os 4 serviços Up).
Opções: `--fim "AAAA-MM-DD HH:MM"` (padrão: agora) e `--tema dark` (padrão: claro).

| Arquivo | Slide | Conteúdo |
| --- | --- | --- |
| `ambiente_docker.png` | Ambiente | saída real de `docker compose ps` (api, gerador, prometheus, grafana **Up**) + data e hora |
| `ambiente_targets.png` | Ambiente | Prometheus › Targets com `mecaniqa-django-api` **UP** |
| `dashboard_sucesso.png` | Dashboard 1 | Grafana › *Requisições com Sucesso*, período da coleta, modo quiosque |
| `dashboard_erro.png` | Dashboard 2 | Grafana › *Requisições com Erro*, período da coleta, modo quiosque |
| `coleta_grafana_3dias.png` | Coleta | painéis "por hora" de sucesso e erro empilhados, período inteiro |

Cada print do Grafana e do Prometheus leva uma faixa de legenda embaixo com a tela, o período
e a hora da captura. Também dá para salvar prints manuais aqui com esses mesmos nomes
(`.png` ou `.jpg`). Os PNGs não vão para o Git; o entregável é o PDF dos slides.
