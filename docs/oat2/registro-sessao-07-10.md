# Monitorando a Continuidade — registro de 07/10/2026

Equipe: Macapá. Responsáveis conforme o caderno de 07/10 enviado pela equipe:

| Papel | Responsável |
| --- | --- |
| Piloto | Lenilson Soares |
| Copiloto | Joab Nascimento |
| QA | Arthur Maia |
| Arquiteto | Douglas Leite |
| Scrum Master | Kaique Ribeiro Souza |

As decisões abaixo resumem as respostas registradas no caderno. O board é uma
proposta complementar para revisão da equipe. O relatório técnico descreve a
implementação e suas evidências; Douglas Leite revisa a consolidação da sessão.

## Brainstorm: cegueira operacional

**Decisão registrada:** passar de uma atuação reativa para uma atuação proativa,
instrumentando código e infraestrutura para acompanhar CPU, memória, acessos e
erros HTTP. A equipe pretende usar essas informações para identificar gargalos e
entender o comportamento das aplicações.

**Alcance da entrega de hoje:** o simulador expõe CPU e memória do processo Python,
quantidade de leituras, sucesso, erro de validação e duração do processamento.
Ainda não há coleta do consumo total dos Pods/nós nem contador geral de acessos
ou de erros HTTP. Logs registram rejeições. Rastreamento distribuído não foi
implementado. Os picos de 8h e 17h serão reproduzidos no teste de carga.

## Brainstorm: stack de monitoramento

**Decisão registrada:** subir Prometheus e Grafana no cluster, instrumentar o
simulador com `/metrics` e criar uma visualização inicial de leituras, taxa de
erro, CPU/memória dos Pods e latência.

**Execução por encontro:** em 07/10, Python instrumentado e Prometheus; em 14/10,
Grafana e exatamente quatro dashboards: CPU, memória, erro e sucesso. Uma
visualização inicial não substitui os quatro dashboards exigidos.

Na implementação atual, Prometheus descobre os Pods pelo Kubernetes e faz scrapes
a cada 10 segundos, armazenando o histórico em PVC. Grafana consultará Prometheus
por PromQL; o simulador não enviará métricas diretamente para Grafana. As séries
de cada réplica são identificadas por Pod. A duração medida é de processamento,
não latência de rede de ponta a ponta.

## Brainstorm guiado: desafio do tráfego

**Resposta registrada:** verificar somente se o servidor está ligado não revela
sobrecarga ou degradação da aplicação durante os picos de leituras IoT. CPU e
memória podem se tornar gargalos mesmo com a máquina disponível. O planejamento
inclui monitoramento dos recursos e HPA para atender aos picos.

A ausência de HPA, por si só, não comprova indisponibilidade: capacidade, carga e
tempo de resposta precisam ser medidos. A meta de 99,9% será formalizada na etapa
de continuidade; os testes atuais não comprovam seu cumprimento.

## Board — proposta para revisão da equipe

| Fatos | Questões | Ideias |
| --- | --- | --- |
| A OAT 1 contém Java, MySQL, Redis, Compose, Kubernetes e Terraform. | A versão Python do professor será disponibilizada? | Adaptar o gerador mantendo a interface de instrumentação. |
| O caderno pede Python instrumentado e Prometheus no Kubernetes em 07/10. | Qual coleta de CPU/memória o professor espera: processo, container ou nó? | Complementar com métricas de infraestrutura para os dashboards. |
| A base Java atual responde HTTP; não implementa consultas de negócio no banco/cache. | Qual carga representa os picos das oficinas? | Definir taxa, duração e critério de sucesso antes do HPA. |
| O simulador desta entrega usa dados sintéticos. | Quais eventos devem originar os dois alertas personalizados? | Avaliar rejeições de leitura e indisponibilidade com a equipe. |
| A taxa de erro configurada é uma probabilidade didática. | Quais responsáveis assumirão alertas e recuperação? | Registrar responsáveis e ações nos runbooks. |

## Relatório técnico da implementação

O código separa regras de domínio, processamento, protocolo HTTP e instrumentação.
As leituras são validadas e classificadas como sucesso/erro. O simulador possui
configuração por ambiente, geração reproduzível, encerramento por sinal e limite
de tamanho para requisições. Há testes de dados inválidos, concorrência,
instrumentação, protocolo e configuração.

Os manifestos usam requests/limits e probes. O simulador roda sem root, sem token
de ServiceAccount e com filesystem somente leitura. O Prometheus usa permissão
restrita de leitura de Pods no namespace, Services internos e PVC para histórico.
Retenção configurada: sete dias e limite de 1 GB de séries, em PVC de 2 GiB.
PVC não é backup e não comprova RPO/RTO.

Na base da OAT 1, a rota Java `/health` foi restringida ao caminho exato e o
manifesto Redis passou a habilitar AOF, alinhando-o ao Compose e Terraform.
AOF com política padrão não garante perda zero nem substitui backup.

## Evidências e fechamento pelo QA

Executar `scripts/check-oat2.ps1` e `scripts/test-oat2.ps1`. Conferir target UP,
leituras HTTP 200/422 e consultas retornando ambos os resultados.
Consultar [validação local](validacao-07-10.md) para os resultados medidos.
As saídas brutas ficam em `out/oat2-2026-10-07/`, ignorado pelo Git.

Antes da submissão, a equipe deve revisar o board e o relatório, confirmar commit/push
na branch principal e comprovação visível ao professor. Nenhum envio ao Blackboard
ou convite de acesso é comprovado por um teste local.
