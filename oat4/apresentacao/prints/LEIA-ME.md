# Prints da apresentação (OAT 4)

O professor valoriza **imagens grandes mostrando o que é real**. Os prints são gerados
automaticamente, em alta resolução (2x) e sempre no mesmo padrão, por:

```powershell
cd oat4
py apresentacao/capturar_prints.py --inicio "2026-11-27 17:00"   # 1ª hora cheia da coleta
py coleta/coletar_prometheus.py                                  # exporta a série horária
py apresentacao/capturar_prints.py --analise                     # roda a análise + print do terminal
py apresentacao/gerar_slides.py --pdf                            # coloca os prints nos slides
```

Rode **depois de 01/12 17:00 (fim da coleta), com a pilha ainda no ar** (`docker compose ps` com os 4 serviços Up).
Opções: `--fim "AAAA-MM-DD HH:MM"` (padrão: agora) e `--tema dark` (padrão: claro).

| Arquivo | Slide | Conteúdo |
| --- | --- | --- |
| `ambiente_docker.png` | Ambiente | janela real do Windows PowerShell com `docker compose ps` (4 serviços **Up**) e `Get-Date` |
| `ambiente_targets.png` | Ambiente | Prometheus › Targets com `mecaniqa-django-api` **UP** |
| `painel_sucesso_5.png` | Dashboard sucesso: por hora | painel *Requisições com sucesso por hora* (a série dos modelos) |
| `painel_sucesso_6.png` | Dashboard sucesso: por minuto | painel *Sucessos por minuto (tempo real)* |
| `painel_sucesso_7.png` | Dashboard sucesso: por status | painel *Sucessos por código de status* |
| `painel_erro_5.png` | Dashboard erro: por hora | painel *Requisições com erro por hora* (a série dos modelos) |
| `painel_erro_6.png` | Dashboard erro: 4xx × 5xx | painel *Erros por classe (4xx x 5xx) por minuto* |
| `painel_erro_7.png` | Dashboard erro: taxa de erro | painel *Taxa de erro (%) ao longo do tempo* |
| `analise_terminal.png` | Análise executada | janela real do Windows PowerShell rodando `analise/analise_oat4.py` (ranking P4) e `Get-Date` |

Cada painel do Grafana é capturado sozinho (um por slide). Os dois terminais são janelas de verdade do Windows PowerShell, abertas e fotografadas por
`apresentacao/janela_terminal.ps1` (fora do Windows, a saída real é desenhada). Cada print do
Grafana e do Prometheus leva uma faixa de legenda embaixo com a tela, o período
e a hora da captura. Também dá para salvar prints manuais aqui com esses mesmos nomes
(`.png` ou `.jpg`). Os PNGs não vão para o Git; o entregável é o PDF dos slides.
