# OAT 2 — teste da etapa de 14/10

Nesta etapa, vamos subir o Grafana, conectá-lo ao Prometheus e conferir quatro painéis: CPU dos Pods, memória dos Pods, erros e sucessos das leituras IoT.

## Antes de começar

Abra o PowerShell na pasta do projeto e confira se o Docker Desktop terminou de iniciar o Kubernetes:

```powershell
docker version
kubectl config current-context
kubectl get nodes
kubectl get storageclass
```

Os nós devem aparecer como `Ready` e o cluster deve ter uma StorageClass padrão para os volumes do Prometheus e do Grafana. Os scripts usam o contexto Kubernetes ativo; se houver mais de um, selecione o contexto da equipe antes de continuar.

## Conferir e subir a stack

Faça a verificação local antes de aplicar os recursos:

```powershell
.\scripts\check-oat2.ps1
kubectl kustomize k8s/oat2
```

O Grafana usa um Secret local chamado `grafana-admin`. Crie-o no mesmo contexto que será usado pelo deploy. A senha é solicitada sem aparecer na tela e não fica salva no repositório:

```powershell
kubectl apply -f .\k8s\oat2\namespace.yaml
$senhaSegura = Read-Host 'Senha do Grafana' -AsSecureString
$ponteiroSenha = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($senhaSegura)
try {
    $env:GRAFANA_ADMIN_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ponteiroSenha)
    kubectl create secret generic grafana-admin `
      --namespace mecaniqa `
      --from-literal=admin-user=admin `
      --from-literal="admin-password=$env:GRAFANA_ADMIN_PASSWORD" `
      --dry-run=client -o yaml | kubectl apply -f -
    if ($LASTEXITCODE -ne 0) { throw 'Não foi possível criar o Secret do Grafana.' }
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ponteiroSenha)
    Remove-Item Env:GRAFANA_ADMIN_PASSWORD -ErrorAction SilentlyContinue
    $senhaSegura.Dispose()
}
```

Suba a aplicação, Prometheus e Grafana:

```powershell
.\scripts\start-oat2.ps1
kubectl get deployments,pods,svc,pvc -n mecaniqa
```

O comando termina quando os três Deployments estão prontos. Os PVCs `prometheus-data` e `grafana-data` devem ficar `Bound`.

## Testar a coleta

O teste automatizado envia uma leitura válida e outra inválida. Também confere se Prometheus está coletando as métricas da aplicação e as métricas de CPU e memória dos Pods pelo Kubelet:

```powershell
.\scripts\test-oat2.ps1
```

Se o teste indicar que o target `kubelet-cadvisor` está indisponível, confira `kubectl get nodes`, as permissões `nodes/metrics` e os logs do Prometheus:

```powershell
kubectl logs deployment/prometheus -n mecaniqa --tail=100
```

Para conferir os gráficos, abra dois terminais. Deixe cada encaminhamento rodando em seu próprio terminal:

```powershell
kubectl port-forward -n mecaniqa svc/prometheus 9090:9090
kubectl port-forward -n mecaniqa svc/grafana 3000:3000
```

No Prometheus (`http://127.0.0.1:9090/targets`), os targets `mecaniqa-iot` e `kubelet-cadvisor` devem aparecer como `UP`. No Grafana (`http://127.0.0.1:3000`), entre com o usuário `admin` e a senha definida ao criar o Secret `grafana-admin`. Essa senha não tem valor padrão e não fica registrada no repositório. Após entrar, abra a pasta **MecaniQA** e confira os quatro painéis. Se não lembrar a senha, será necessário redefinir a senha de administrador do Grafana; recriar apenas o Secret pode não alterá-la se o Grafana já tiver sido inicializado.

As consultas principais são:

```promql
sum by (pod) (rate(container_cpu_usage_seconds_total{job="kubelet-cadvisor",namespace="mecaniqa",pod!="",container!="",container!="POD"}[5m]))
sum by (pod) (container_memory_working_set_bytes{job="kubelet-cadvisor",namespace="mecaniqa",pod!="",container!="",container!="POD"})
sum by (pod) (rate(mecaniqa_iot_readings_total{result="error"}[5m]))
sum by (pod) (rate(mecaniqa_iot_readings_total{result="success"}[5m]))
```

Os gráficos de erro e sucesso mostram leituras que chegaram à validação da aplicação. Eles não contam todos os erros HTTP. CPU e memória vêm do Kubelet/cAdvisor e representam os containers dos Pods.

## O que falta para a entrega final

Depois de testar os painéis, a equipe deve revisar os arquivos e versioná-los na branch `main`, como pede a atividade. Os alarmes, o HPA e o teste de estresse são da próxima etapa, em 21/10. Runbooks, SLA, SLO, SLI, RTO e RPO também ficam para o fechamento.
