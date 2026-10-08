# OAT 2 — validação local de 07/10/2026

Resultados obtidos nesta máquina, no Docker Desktop e no contexto Kubernetes
`docker-desktop`. Horários locais em UTC−03:00. Os logs dos containers usam UTC;
por isso alguns registros aparecem como 08/10, embora a execução local seja 07/10.

## Resultados verificados

| Verificação | Resultado |
| --- | --- |
| Testes Python | 10 testes aprovados; inclui 40 leituras HTTP concorrentes sem perda de contagem |
| Qualidade Python | `ruff check` e `ruff format --check` aprovados |
| Configuração Prometheus | Dois arquivos aprovados por `promtool check config --syntax-only` |
| Compose | Configuração válida e coleta real aprovada; simulador saudável |
| Kubernetes | Dry-run no servidor e aplicação aprovados; simulador e Prometheus disponíveis |
| Leituras HTTP | Leitura válida aceita (200); tensão negativa rejeitada (422) |
| Métricas | Contadores, histograma, gauge, CPU e memória presentes |
| Coleta real | Target IoT UP e consultas PromQL retornando sucesso e erro |
| Descoberta de réplicas | Duas réplicas temporárias descobertas separadamente, ambas UP |
| Persistência Prometheus | Consulta no mesmo instante histórico retornou **186** antes e depois do restart |
| Recuperação simulador | Rollout concluído após restart; restaurado para uma réplica |
| Regressão Java | Sete checks aprovados em container separado; `/healthXYZ` e `/health/extra` retornaram 404 |
| Redis AOF | `appendonly=yes`; chave sintética sobreviveu a SIGKILL do container no namespace de teste |
| PowerShell | Sintaxe de todos os scripts aprovada pelo parser |
| Diff | `git diff --check` aprovado |

No teste Redis, o contador de reinicializações passou de 0 para 1. A chave foi
removida depois da verificação. A queda foi provocada via runtime do container,
não por um `kill` ignorado pelo processo PID 1. Houve espera de dois segundos
antes da queda, respeitando a janela de fsync padrão; o teste não comprova perda
zero para gravações imediatamente anteriores à falha.

## Evidências locais

Diretório: `out/oat2-2026-10-07/` (ignorado pelo Git).

- `runtime-Kubernetes.json`: saúde, rejeição, targets e respostas PromQL.
- `runtime-Compose.json`: mesmo fluxo no Compose.
- `recovery-Kubernetes.json`: duas réplicas e consulta histórica antes/depois.
- `redis-aof-recovery.json`: configuração AOF, queda e persistência.
- `metrics.txt`: exposição de métricas capturada pelo teste.
- `applied-manifest.yaml`: manifesto aplicado com tag de imagem única.
- `cluster-final.txt`: Pods, Services e PVC do ambiente OAT 2.

Validação Kubernetes final realizada às **21:51:06**, com imagem do simulador
`mecaniqa-iot:2.0-20261007215031`. PVC do Prometheus Bound, 2 GiB, StorageClass
`standard`. A consulta histórica de persistência foi realizada às 21:48.

Após os testes, o Compose da OAT 2 foi parado preservando seu volume. O simulador
e Prometheus permanecem ativos no Kubernetes; use port-forward para demonstrar.

## Alcance da comprovação

O namespace `mecaniqa` contém os novos recursos IoT e Prometheus. A base da OAT 1
foi exercitada anteriormente no namespace de laboratório
`mecaniqa-aula-20261007` e em Compose. A regressão Java desta revisão foi verificada
em container descartável; os containers antigos da OAT 1 não foram substituídos
automaticamente por essa imagem corrigida. Para atualizar a base em uso, rebuild
e rollout são necessários conforme o procedimento da OAT 1.

O teste com duas réplicas usa escala manual, não HPA. Não houve implementação de
Grafana, quatro dashboards, quatro alertas ou plano final de continuidade nesta
sessão. Esses itens pertencem às próximas etapas do caderno.

Arquivos preparados localmente; nenhum commit, push ou envio ao Blackboard foi
realizado nesta implementação. Os responsáveis e as decisões foram atualizados
com base no caderno enviado pela equipe; o board permanece uma proposta para
revisão. As evidências comprovam o laboratório local, não um SLA em produção.
