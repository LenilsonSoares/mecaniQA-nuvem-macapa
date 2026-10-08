# MecaniQA — OAT 1: Docker, Docker Compose e Kubernetes

Projeto acadêmico de conteinerização e orquestração de uma API Java do MecaniQA, com MySQL e Redis provisionados para a aplicação, Docker Compose para execução local, Kubernetes/Minikube para orquestração e Terraform para provisionamento declarativo.

## Equipe

- Nome da equipe: **Macapá**
- Unidade: **Vitória da Conquista**
- Integrantes:
  - Artur Maia Coqueiro
  - Douglas Renan Santos
  - Kayky Ribeiro Souza
  - Lenilson Dias Soares
  - Joab Nascimento Rodrigues

## Arquitetura

```text
Cliente
  |
  v
API Java :8080
  |
  +-----------> MySQL :3306 e Redis :6379 (serviços internos)
```

No Compose, os nomes `db` e `cache` funcionam como DNS interno. No Kubernetes, Services `ClusterIP` oferecem os mesmos nomes. Apenas a API é exposta externamente.

## Estrutura principal

```text
.
|-- Dockerfile                     # imagem multi-stage da API Java
|-- docker-compose.yml             # execução local dos três serviços
|-- docker/mysql/Dockerfile        # imagem do MySQL
|-- docker/redis/Dockerfile        # imagem do Redis com AOF
|-- mecaniqa-k8s.yaml              # Namespace, Secret, PVCs, Deployments e Services
|-- terraform/                     # infraestrutura Kubernetes como código
|-- src/br/com/mecaniqa/Application.java
`-- mecaniQA_oat1_macapa.pdf       # apresentação final para versionamento
```

## Pré-requisitos

- Docker Desktop com Docker Compose v2;
- kubectl e Kubernetes do Docker Desktop para a etapa Kubernetes;
- Terraform 1.5 ou superior para a etapa de IaC.

No Docker Desktop, habilite o Kubernetes em **Settings > Kubernetes > Enable Kubernetes** e aguarde o status `Running`. Depois confirme no PowerShell:

```powershell
kubectl config use-context docker-desktop
kubectl get nodes
```

## 1. Executar com Docker Compose

Crie o arquivo local de ambiente sem versionar a senha:

```powershell
Copy-Item .env.example .env
# Edite .env e defina uma senha forte.
docker compose up --build -d
docker compose ps
```

Valide a API e a persistência:

```powershell
Invoke-RestMethod http://localhost:8080/
Invoke-RestMethod http://localhost:8080/health
docker compose restart db cache
docker compose ps
```

Resultado esperado do endpoint de saúde:

```json
{"service":"mecaniqa-api","status":"UP"}
```

Nesta versão, a API mínima expõe `/` e `/health`. As variáveis `DB_*` e `REDIS_*` já são entregues pelos ambientes Compose e Kubernetes para a próxima etapa de integração; os endpoints atuais não executam consultas nem operações de cache.

Para encerrar sem apagar os volumes:

```powershell
docker compose down
```

Use `docker compose down -v` somente quando quiser apagar os dados persistidos.

## 2. Executar no Kubernetes

Com o contexto `docker-desktop` ativo, construa a imagem no Docker Engine local. O cluster `kind` do Docker Desktop consegue utilizá-la:

```powershell
docker compose build api
kubectl config use-context docker-desktop
kubectl get nodes
```

Crie o namespace e o Secret antes dos workloads. O valor real não fica salvo no manifesto nem no repositório:

```powershell
$env:MYSQL_ROOT_PASSWORD = "troque-por-uma-senha-forte"
kubectl create namespace mecaniqa --dry-run=client -o yaml | kubectl apply -f -
kubectl create secret generic mecaniqa-secrets `
  --namespace mecaniqa `
  --from-literal=mysql-root-password=$env:MYSQL_ROOT_PASSWORD `
  --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f mecaniqa-k8s.yaml
```

> Em produção, use um gerenciador de segredos e nunca armazene credenciais no Git.

Verifique o resultado:

```powershell
kubectl get all,pvc -n mecaniqa
kubectl get pods -n mecaniqa -w
kubectl port-forward -n mecaniqa service/api-service 8081:8080
```

Em Minikube, substitua a etapa de build por `minikube image build -t mecaniqa-api:1.1 .` e use `minikube service` para obter a URL.

No Kubernetes do Docker Desktop, use um encaminhamento local para testar a API:

```powershell
kubectl port-forward -n mecaniqa service/api-service 8081:8080
Invoke-RestMethod http://localhost:8081/health
```

Resultado esperado: quatro Pods `Running` e `Ready 1/1` — duas réplicas da API, um MySQL e um Redis — além de dois PVCs `Bound`.

Monitoramento com K9s:

```powershell
k9s -n mecaniqa
```

## 3. Provisionar com Terraform

O Terraform cria o mesmo namespace e seus recursos. Não aplique o YAML e o Terraform ao mesmo tempo em um cluster limpo: escolha uma das duas estratégias para evitar disputa de gerenciamento.

```powershell
Set-Location terraform
$env:TF_VAR_mysql_root_password = "troque-por-uma-senha-forte"
terraform init
terraform fmt -check
terraform validate
terraform plan
terraform apply
```

O provider usa por padrão `~/.kube/config` e o contexto `docker-desktop`. Ajuste `kube_context` ou `kubeconfig_path` quando necessário. Variáveis sensíveis não aparecem normalmente na saída, mas a senha ainda pode existir no estado: proteja o arquivo de estado e prefira backend remoto com controle de acesso em ambientes reais.

Para remover somente os recursos gerenciados pelo Terraform:

```powershell
terraform destroy
```

## Endpoints e portas

| Componente | Porta | Acesso |
| --- | ---: | --- |
| API Java | 8080 | localhost no Compose; port-forward no Docker Desktop; NodePort 30080 no Minikube |
| MySQL | 3306 | publicado no Compose; interno no Kubernetes |
| Redis | 6379 | publicado no Compose; interno no Kubernetes |

## Controles implementados

- Build multi-stage e usuário não-root para a API;
- health checks no Docker Compose e probes no Kubernetes;
- volumes nomeados no Compose e PVCs no Kubernetes;
- rede dedicada e descoberta por DNS;
- Secret referenciado pelo MySQL, sem senha real versionada;
- `requests` e `limits` de CPU/memória nos três Deployments;
- Terraform equivalente ao manifesto Kubernetes;
- duas réplicas da API com auto-healing gerenciado por Deployment.

## Evidências esperadas

- `docker compose ps`: três serviços em execução e saudáveis;
- `GET /health`: HTTP 200 com status `UP`;
- `kubectl get pods -n mecaniqa`: quatro Pods `1/1 Running`;
- K9s: duas réplicas da API, MySQL e Redis sem reinicializações durante a demonstração;
- dados mantidos após reiniciar containers/Pods, graças a volumes e PVCs.

## Teste rápido automatizado

Com a stack do Compose em execução, rode:

```powershell
.\scripts\smoke-test.ps1
```

O script verifica os endpoints principais, a resposta `404` para rotas inexistentes e `405` para métodos HTTP não permitidos.

## OAT 2 — Monitorando a Continuidade

A sessão de **07/10/2026** acrescenta o simulador Python instrumentado e Prometheus
ao Kubernetes. Consulte o [roteiro completo do piloto](docs/oat2/guia-piloto-07-10.md),
o [board e registro da sessão](docs/oat2/registro-sessao-07-10.md) e a
[validação local](docs/oat2/validacao-07-10.md).

```powershell
.\scripts\check-oat2.ps1
.\scripts\start-oat2.ps1
.\scripts\test-oat2.ps1
```

Os recursos ficam em `iot/` e `k8s/oat2/`; o ambiente alternativo de desenvolvimento
usa `docker-compose.oat2.yml`. Grafana, alertas, HPA e continuidade são entregas das
próximas sessões e estão detalhados no roteiro.

## Entrega da OAT 1

O arquivo `mecaniQA_oat1_macapa.pdf` deve permanecer na raiz do repositório, ser versionado na branch principal e também enviado ao formulário do Blackboard. Tempo máximo da apresentação: sete minutos.
