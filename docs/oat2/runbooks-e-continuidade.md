# OAT 2 — Runbooks e Plano de Continuidade

**Equipe:** Macapá · **Sistema:** ingestão IoT do MecaniQA (`mecaniqa-iot`) · **Namespace:** `mecaniqa`

Este documento consolida a entrega final da OAT 2: o passo a passo de troubleshooting para cada um dos
quatro alarmes do Grafana e as metas de serviço (SLA, SLO, SLI, RTO e RPO). As evidências do teste de
estresse estão em [`docs/evidencias/`](../evidencias/README.md).

## 1. Metas de serviço

| Sigla | Definição | Meta da MecaniQA | Como medimos |
| --- | --- | --- | --- |
| **SLA** | Compromisso contratual com as oficinas (clientes Enterprise) | 99,9% de disponibilidade mensal da ingestão IoT (até 43,2 min fora do ar por mês; 8 h 45 min por ano) | Relatório mensal a partir do SLI de disponibilidade |
| **SLO** | Meta interna, mais rígida que o SLA, para haver margem antes de quebrar o contrato | 99,95% das checagens de `/health` com HTTP 200 no mês (até 21,6 min fora) | Probes do Kubernetes e consultas ao Prometheus |
| **SLI** | Indicador medido de fato | (1) % de checagens de `/health` com HTTP 200; (2) leituras aceitas ÷ leituras recebidas (`mecaniqa_iot_readings_total`) | Prometheus e painéis de Sucesso e Erros no Grafana |
| **RTO** | Tempo máximo para restabelecer o serviço após uma falha | 15 minutos para voltar a receber leituras | Tempo entre o alarme e o retorno do `/health` 200 |
| **RPO** | Perda máxima de dados aceitável | Até 24 h do histórico de métricas | Snapshot diário do PVC do Prometheus (a implementar) |

**Por que o RTO é 15 minutos:** o orçamento de erro mensal do SLA é de 43,2 minutos. Com RTO de 15 min,
a equipe absorve até duas falhas graves no mês sem quebrar o contrato.

**Pergunta do encontro — região de nuvem fora por 45 minutos:** quem determina o tempo para voltar ao ar
é o **RTO**; o RPO determina quantos dados podem ser perdidos. Uma queda de 45 minutos supera o orçamento
mensal de 43,2 min e quebraria o SLA daquele mês. No recorte anual (8 h 45 min de tolerância), consumiria
cerca de 8,6% do orçamento. Por isso o RTO precisa ficar abaixo de 43 min, e a meta da equipe é 15 min.

**Limites honestos:** essas metas são da equipe e não foram comprovadas em produção. O teste foi feito
em um cluster local de um nó, e o PVC do Prometheus não é backup.

## 2. Alarmes cobertos

Regras provisionadas em [`k8s/oat2/grafana-alerting.yaml`](../../k8s/oat2/grafana-alerting.yaml). Cada
regra precisa ficar **30 s** acima do limiar para disparar, o que evita falso positivo em picos isolados.

| Alarme | Condição | Tipo |
| --- | --- | --- |
| 1. CPU | CPU somada do simulador > 0,075 núcleo (75% da request de 100m) | Infraestrutura |
| 2. Memória | Memória de trabalho somada > 100 MiB (limite do container: 128 MiB) | Infraestrutura |
| 3. Erros | Leituras rejeitadas > 5 por minuto | Aplicação |
| 4. Sucessos / volume | Leituras aceitas > 50 por minuto | Aplicação |

O HPA ([`k8s/oat2/hpa.yaml`](../../k8s/oat2/hpa.yaml)) escala de 1 a 5 Pods com alvo de 60% de CPU e
70% de memória. Em operação normal, ele reage antes de o problema virar indisponibilidade.

## 3. Runbooks

Todos os comandos usam o namespace `mecaniqa`. Para abrir os painéis:
`kubectl port-forward -n mecaniqa svc/grafana 3000:3000`.

### Runbook 1 — CPU alta

1. **Confirmar o HPA:** `kubectl get hpa mecaniqa-iot-hpa -n mecaniqa`
   - Réplicas abaixo de 5: o HPA está escalando. Acompanhe por 2 a 3 minutos.
   - Réplicas em 5/5: a capacidade máxima foi atingida. Siga para o passo 2.
2. **Ver o consumo por Pod:** `kubectl top pods -n mecaniqa -l app=mecaniqa-iot`
3. **Ver os eventos de escala:** `kubectl describe hpa mecaniqa-iot-hpa -n mecaniqa`
4. **Mitigar:**
   - Pico esperado (8h ou 17h) e tráfego legítimo: aumentar `maxReplicas` no `hpa.yaml` e reaplicar com `kubectl apply -k k8s/oat2`.
   - CPU alta com volume normal: suspeitar de regressão de código. Comparar com o painel de Sucessos e reverter com `kubectl rollout undo deployment/mecaniqa-iot -n mecaniqa`.
5. **Encerrar:** o alarme volta a Normal e a CPU fica abaixo do alvo de 60%.

### Runbook 2 — Memória alta

1. **Ver o consumo:** `kubectl top pods -n mecaniqa -l app=mecaniqa-iot`
2. **Procurar reinícios e OOMKilled:** `kubectl get pods -n mecaniqa -l app=mecaniqa-iot` (coluna RESTARTS) e
   `kubectl describe pod <pod> -n mecaniqa` (campo `Last State: OOMKilled`).
3. **Separar carga de vazamento:**
   - A memória sobe junto com o volume e cai depois da carga: comportamento normal. O HPA cuida.
   - A memória só sobe, mesmo com o volume estável: provável vazamento.
4. **Mitigar:**
   - Vazamento: `kubectl rollout restart deployment/mecaniqa-iot -n mecaniqa` (reinício gradual, sem derrubar o serviço) e abrir correção no código.
   - Limite apertado para a carga real: revisar `resources.limits.memory` em `iot.yaml`.
5. **Encerrar:** a memória estabiliza abaixo de 100 MiB e não há novos reinícios.

### Runbook 3 — Erros de leitura

1. **Medir a proporção no painel Erros:** erro alto com sucesso também alto indica sensores enviando dados
   inválidos. Erro alto com sucesso caindo indica falha no serviço.
2. **Ler os logs de rejeição:** `kubectl logs -n mecaniqa -l app=mecaniqa-iot --tail=100`
3. **Classificar a causa:**
   - Respostas HTTP 422 (validação): a leitura é inválida, por exemplo tensão negativa. A origem é o sensor ou a oficina.
   - Falhas de saúde do serviço: `kubectl get pods` mostra Pods fora de `1/1 Running`.
4. **Mitigar:**
   - Dados inválidos: identificar o sensor ou a oficina de origem e acionar o responsável. O serviço está protegendo os dados.
   - Falha do serviço: seguir o Runbook 1 ou 2, ou reverter a última versão com `kubectl rollout undo`.
5. **Encerrar:** as rejeições voltam a ficar abaixo de 5 por minuto.

### Runbook 4 — Volume de sucessos alto

Este alarme é **informativo**: avisa que o tráfego está acima do normal antes que vire problema.

1. **Verificar o horário:** picos às 8h e às 17h são esperados.
2. **Acompanhar o HPA:** `kubectl get hpa mecaniqa-iot-hpa -n mecaniqa -w`
3. **Cruzar com os outros painéis:** se CPU, memória e erros estão normais, o sistema está absorvendo a carga.
4. **Escalar a resposta** se o volume vier junto com o alarme de CPU ou de Erros: seguir o runbook correspondente e avisar a equipe.
5. **Encerrar:** o volume volta ao patamar normal e o HPA reduz as réplicas.

## 4. Recuperação de desastre

Se o cluster ou a região ficar indisponível:

1. Provisionar um cluster novo (ou outro contexto do `kubectl`).
2. Reaplicar toda a stack versionada: `kubectl apply -k k8s/oat2`
3. Validar com `scripts/test-oat2.ps1`: saúde, leitura válida, rejeição 422 e métricas.
4. Restaurar o snapshot do PVC do Prometheus, se existir. Sem snapshot, o histórico recomeça do zero, o que está dentro do RPO de 24 h apenas se houver backup diário.

Como toda a infraestrutura está declarada em YAML no repositório, reaplicar a stack leva poucos minutos.
Isso é o que torna o RTO de 15 minutos viável.

## 5. Critério de sucesso do teste de estresse

Resultado da execução registrada em [`docs/evidencias/README.md`](../evidencias/README.md):

| Critério | Resultado |
| --- | --- |
| HPA escala sem intervenção manual | 1 → 5 réplicas em cerca de 45 s |
| Os 4 alarmes disparam | 4 regras em Firing durante a carga |
| Sem `OOMKilled` nem `CrashLoopBackOff` | 0 reinícios |
| Redução após a carga | HPA reduziu as réplicas ao fim do teste |
