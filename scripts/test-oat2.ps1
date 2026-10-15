[CmdletBinding()]
param(
    [ValidateSet('Kubernetes', 'Compose')][string]$Mode = 'Kubernetes',
    [string]$Context,
    [int]$IotPort = 18000,
    [int]$PrometheusPort = 19090
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$evidence = Join-Path $repoRoot 'out/oat2-2026-10-07'
New-Item -ItemType Directory -Path $evidence -Force | Out-Null
$tunnels = @()
try {
    if ($Mode -eq 'Kubernetes') {
        if ([string]::IsNullOrWhiteSpace($Context)) {
            $Context = kubectl config current-context
            if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($Context)) {
                throw 'Não encontrei um contexto Kubernetes ativo. Confira kubectl config current-context.'
            }
            $Context = $Context.Trim()
        }
        foreach ($target in @(@('mecaniqa-iot', "$($IotPort):8000"), @('prometheus', "$($PrometheusPort):9090"))) {
            $name = $target[0]
            $arguments = @('--context', $Context, '-n', 'mecaniqa', 'port-forward', "svc/$name", $target[1], '--address=127.0.0.1')
            $tunnels += Start-Process kubectl -ArgumentList $arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $evidence "$name-forward.log") -RedirectStandardError (Join-Path $evidence "$name-forward-error.log")
        }
    } else {
        $IotPort = 8000
        $PrometheusPort = 9090
    }
    $iot = "http://127.0.0.1:$IotPort"
    $prometheus = "http://127.0.0.1:$PrometheusPort"
    $ready = $false
    for ($attempt = 0; $attempt -lt 45; $attempt++) {
        try {
            $health = Invoke-RestMethod "$iot/health" -TimeoutSec 2
            $targets = Invoke-RestMethod "$prometheus/api/v1/targets" -TimeoutSec 2
            $iotTargets = @($targets.data.activeTargets | Where-Object { $_.labels.job -eq 'mecaniqa-iot' })
            $kubeletReady = $true
            if ($Mode -eq 'Kubernetes') {
                $kubeletTargets = @($targets.data.activeTargets | Where-Object { $_.labels.job -eq 'kubelet-cadvisor' })
                $kubeletReady = $kubeletTargets.Count -gt 0 -and @($kubeletTargets | Where-Object health -ne 'up').Count -eq 0
            }
            if ($health.status -eq 'UP' -and $iotTargets.Count -gt 0 -and @($iotTargets | Where-Object health -ne 'up').Count -eq 0 -and $kubeletReady) {
                $ready = $true
                break
            }
        } catch { }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) { throw 'Simulador, target da aplicação ou target Kubelet/cAdvisor indisponível após 45 tentativas. Confira /targets e os logs do Prometheus.' }
    $valid = Invoke-RestMethod "$iot/readings" -Method Post -ContentType 'application/json' -Body '{"sensor_type":"engine_temperature","value":90}'
    if ($valid.status -ne 'success') { throw 'Leitura válida não foi aceita.' }
    try {
        Invoke-RestMethod "$iot/readings" -Method Post -ContentType 'application/json' -Body '{"sensor_type":"battery_voltage","value":-1}' | Out-Null
        throw 'Leitura inválida foi aceita.'
    } catch {
        if (-not $_.Exception.Response -or [int]$_.Exception.Response.StatusCode -ne 422) { throw }
    }
    $metrics = (Invoke-WebRequest "$iot/metrics" -UseBasicParsing).Content
    $metrics | Set-Content (Join-Path $evidence 'metrics.txt') -Encoding utf8
    foreach ($name in @('mecaniqa_iot_readings_total', 'mecaniqa_iot_processing_duration_seconds', 'process_resident_memory_bytes', 'process_cpu_seconds_total')) {
        if ($metrics -notmatch $name) { throw "Métrica ausente: $name" }
    }
    $queries = @{}
    foreach ($result in @('success', 'error')) {
        $query = 'sum(mecaniqa_iot_readings_total{source="http",result="' + $result + '"})'
        $collected = $false
        for ($attempt = 0; $attempt -lt 30; $attempt++) {
            $response = Invoke-RestMethod "$prometheus/api/v1/query?query=$([uri]::EscapeDataString($query))"
            if ($response.status -eq 'success' -and $response.data.result.Count -gt 0 -and [double]$response.data.result[0].value[1] -ge 1) {
                $collected = $true
                $queries[$result] = $response
                break
            }
            Start-Sleep -Seconds 1
        }
        if (-not $collected) { throw "Prometheus não coletou a leitura: $result" }
    }
    $resourceQueries = @{}
    if ($Mode -eq 'Kubernetes') {
        $podMetrics = @{
            cpu = 'sum by (pod) (rate(container_cpu_usage_seconds_total{job="kubelet-cadvisor",namespace="mecaniqa",pod!="",container!="",container!="POD"}[1m]))'
            memory = 'sum by (pod) (container_memory_working_set_bytes{job="kubelet-cadvisor",namespace="mecaniqa",pod!="",container!="",container!="POD"})'
        }
        foreach ($metric in $podMetrics.Keys) {
            $collected = $false
            $query = $podMetrics[$metric]
            for ($attempt = 0; $attempt -lt 45; $attempt++) {
                $response = Invoke-RestMethod "$prometheus/api/v1/query?query=$([uri]::EscapeDataString($query))"
                if ($response.status -eq 'success' -and $response.data.result.Count -gt 0) {
                    $collected = $true
                    $resourceQueries[$metric] = $response
                    break
                }
                Start-Sleep -Seconds 1
            }
            if (-not $collected) { throw "Prometheus não encontrou métricas de $metric dos Pods no Kubelet/cAdvisor." }
        }
    }
    $targets = Invoke-RestMethod "$prometheus/api/v1/targets"
    $report = [ordered]@{ verifiedAt = (Get-Date).ToString('o'); mode = $Mode; context = $Context; health = $health; validReading = $valid; rejectedStatus = 422; targets = $targets; queries = $queries; podResourceQueries = $resourceQueries }
    $report | ConvertTo-Json -Depth 20 | Set-Content (Join-Path $evidence "runtime-$Mode.json") -Encoding utf8
    $message = 'Teste aprovado: saúde, leitura válida, rejeição 422 e métricas da aplicação.'
    if ($Mode -eq 'Kubernetes') { $message += ' CPU e memória dos Pods também foram coletadas.' }
    Write-Host "$message Evidências: $evidence"
} finally {
    foreach ($tunnel in $tunnels) {
        if (-not $tunnel.HasExited) { Stop-Process -Id $tunnel.Id -ErrorAction SilentlyContinue }
    }
}
