# OAT 2 — registro da sessão de 14/10

**Problema:** Monitorando a Continuidade  
**Equipe:** Macapá

## Papéis

| Papel | Integrante |
| --- | --- |
| Piloto | Kayky Ribeiro |
| Copiloto | Lenilson Dias |
| QA | Joab Nascimento |
| Arquiteto | Artur Maia |
| Scrum Master | Douglas Renan |

## Respostas do encontro

### Como o Prometheus coleta as métricas?

O simulador precisa expor as métricas em um endpoint HTTP para o Prometheus consultar. A biblioteca usada no Python é `prometheus_client`; contadores registram leituras aceitas e rejeitadas. Neste projeto, a aplicação já publica `/metrics` na porta 8000. O Prometheus consulta esse endpoint a cada 10 segundos.

### Quais são os quatro dashboards?

1. **CPU dos Pods:** uso de CPU dos containers, vindo do endpoint `/metrics/cadvisor` do Kubelet.
2. **Memória dos Pods:** memória de trabalho dos containers, também coletada pelo Kubelet/cAdvisor.
3. **Erros:** leituras rejeitadas pela validação da aplicação.
4. **Sucessos:** leituras aceitas pela aplicação.

CPU e memória vêm da infraestrutura. Erro e sucesso vêm dos contadores da aplicação. Assim, os painéis mostram as duas partes do problema sem tratar métricas do processo Python como se fossem o consumo completo do Pod.

### Por que acompanhar a taxa de erros?

Um aumento de erros pode mostrar que as leituras estão falhando antes de as oficinas perceberem diagnósticos incompletos. A equipe deve comparar esse painel com a taxa de sucesso e com o uso de CPU e memória para investigar a causa.

## O que foi preparado

Foram adicionados o Deployment e o Service do Grafana, a fonte de dados Prometheus e quatro dashboards JSON em `k8s/oat2/`. O Prometheus também ganhou uma configuração para coletar as métricas de CPU e memória do Kubelet/cAdvisor. A permissão concedida ao Prometheus é de leitura de `nodes/metrics` e descoberta dos nós.

O simulador já tinha `prometheus_client` e o endpoint `/metrics`; não foi necessário abrir um segundo servidor HTTP. O contador de erro cobre leituras rejeitadas pela validação do domínio. Ele não conta falhas de protocolo nem mede a disponibilidade HTTP completa.

## Teste da equipe

Depois de o Kubernetes do Docker Desktop ficar pronto, a equipe vai subir os recursos, confirmar os dois targets no Prometheus (`mecaniqa-iot` e `kubelet-cadvisor`) e abrir os quatro painéis no Grafana. O teste automatizado também confere a coleta de CPU e memória dos Pods.

**Status:** arquivos preparados localmente. A execução no cluster e as capturas de tela ainda precisam ser feitas pela equipe antes do commit e da entrega.

## Próxima etapa

Na sessão de 21/10 entram os quatro alertas, o HPA e o teste de estresse. Runbooks e metas de SLA, SLO, SLI, RTO e RPO ficam para o fechamento da OAT 2.
