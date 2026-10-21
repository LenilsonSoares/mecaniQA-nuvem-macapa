[CmdletBinding()]
param(
    [string]$OutputDir = 'out/stress-test',
    [string]$PrometheusUrl = 'http://127.0.0.1:9090',
    [string]$IotUrl = 'http://127.0.0.1:8000'
)

$ErrorActionPreference = 'Continue'
$repoRoot = Split-Path -Parent $PSScriptRoot
$targetDir = Join-Path $repoRoot $OutputDir

if (-not (Test-Path $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
}

$timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
Write-Host "=== MecaniQA - Coleta de Evidencias de Estresse e HPA ===" -ForegroundColor Cyan
Write-Host "Momento da coleta: $timestamp"
Write-Host "Salvando evidencias em: $targetDir`n"

# 1. Coleta do HPA no Kubernetes
Write-Host "[1/5] Capturando estado do HPA..." -ForegroundColor Yellow
$hpaDescribe = kubectl describe hpa mecaniqa-iot-hpa -n mecaniqa 2>&1
$hpaDescribe | Out-File (Join-Path $targetDir "hpa-describe.txt") -Encoding utf8
$hpaYaml = kubectl get hpa mecaniqa-iot-hpa -n mecaniqa -o yaml 2>&1
$hpaYaml | Out-File (Join-Path $targetDir "hpa.yaml") -Encoding utf8

# 2. Coleta das Replicas dos Pods
Write-Host "[2/5] Capturando Pods e distribuicao de replicas..." -ForegroundColor Yellow
$podsWide = kubectl get pods -n mecaniqa -l app=mecaniqa-iot -o wide 2>&1
$podsWide | Out-File (Join-Path $targetDir "pods-scaled.txt") -Encoding utf8
Write-Host $podsWide

# 3. Coleta de Consumo de Recursos (Top Pods)
Write-Host "[3/5] Capturando consumo de CPU e Memoria dos Pods (kubectl top)..." -ForegroundColor Yellow
$topPods = kubectl top pods -n mecaniqa 2>&1
$topPods | Out-File (Join-Path $targetDir "top-pods.txt") -Encoding utf8

# 4. Coleta de Eventos Recentes do Cluster
Write-Host "[4/5] Capturando eventos de escalonamento do Kubernetes..." -ForegroundColor Yellow
$events = kubectl get events -n mecaniqa --sort-by=.metadata.creationTimestamp 2>&1
$events | Out-File (Join-Path $targetDir "k8s-events.txt") -Encoding utf8

# 5. Coleta de Metricas da Aplicacao e Prometheus
Write-Host "[5/5] Coletando snapshots de telemetria..." -ForegroundColor Yellow
try {
    $iotMetrics = (Invoke-WebRequest "$IotUrl/metrics" -UseBasicParsing -TimeoutSec 3).Content
    $iotMetrics | Out-File (Join-Path $targetDir "iot-metrics-snapshot.txt") -Encoding utf8
    Write-Host "  Snapshot de metricas IoT capturado." -ForegroundColor Green
} catch {
    Write-Host "  Nao foi possivel conectar em $IotUrl/metrics." -ForegroundColor Gray
}

try {
    $alerts = Invoke-RestMethod "$PrometheusUrl/api/v1/alerts" -TimeoutSec 3
    $alerts | ConvertTo-Json -Depth 10 | Out-File (Join-Path $targetDir "prometheus-alerts.json") -Encoding utf8
    Write-Host "  Estado dos alertas do Prometheus capturado." -ForegroundColor Green
} catch {
    Write-Host "  Prometheus em $PrometheusUrl nao respondeu (opcional)." -ForegroundColor Gray
}

# Gerar Relatorio Resumo
$reportLines = @(
    "# Evidencias do Teste de Estresse e Escalonamento HPA",
    "**Data/Hora:** $timestamp",
    "**Namespace:** mecaniqa",
    "**Deployment Alvo:** mecaniqa-iot",
    "",
    "## Estado do Horizontal Pod Autoscaler (HPA)",
    "```text",
    $hpaDescribe,
    "```",
    "",
    "## Pods Escalados",
    "```text",
    $podsWide,
    "```",
    "",
    "## Consumo no Pico (kubectl top)",
    "```text",
    $topPods,
    "```",
    "",
    "## Instrucoes para o Piloto / Apresentacao",
    "1. Acesse o Grafana: http://127.0.0.1:3000/alerting/list",
    "   - Capture o print dos 4 alertas disparados (Firing).",
    "2. Acesse os Dashboards de CPU e Memoria: http://127.0.0.1:3000/dashboards",
    "   - Capture o print demonstrando a elevacao do consumo e o surgimento das novas replicas.",
    "3. Salve os prints em 'docs/evidencias/' para compor a entrega da equipe."
)

$reportLines -join [Environment]::NewLine | Out-File (Join-Path $targetDir "relatorio-evidencias.md") -Encoding utf8

Write-Host "`nEvidencias consolidadas em: $targetDir" -ForegroundColor Green
Write-Host "Relatorio gerado em: $(Join-Path $targetDir 'relatorio-evidencias.md')" -ForegroundColor Green
