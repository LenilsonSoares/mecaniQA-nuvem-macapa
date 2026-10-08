[CmdletBinding()]
param([string]$Context = 'docker-desktop', [int]$PrometheusPort = 19091)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$evidence = Join-Path $repoRoot 'out/oat2-2026-10-07'
New-Item -ItemType Directory -Path $evidence -Force | Out-Null
$tunnel = $null
$deployment = kubectl --context $Context get deployment mecaniqa-iot -n mecaniqa -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Simulador não encontrado.' }
$originalReplicas = $deployment.spec.replicas
$baseUrl = "http://127.0.0.1:$PrometheusPort"
function Open-PrometheusTunnel {
    Start-Process kubectl -WindowStyle Hidden -PassThru -ArgumentList @('--context', $Context, '-n', 'mecaniqa', 'port-forward', 'svc/prometheus', "$($PrometheusPort):9090", '--address=127.0.0.1') -RedirectStandardOutput (Join-Path $evidence 'recovery-forward.log') -RedirectStandardError (Join-Path $evidence 'recovery-forward-error.log')
}
function Wait-Prometheus {
    for ($attempt = 0; $attempt -lt 45; $attempt++) {
        try { return Invoke-RestMethod "$baseUrl/api/v1/targets" -TimeoutSec 2 } catch { Start-Sleep -Seconds 1 }
    }
    throw 'Prometheus não respondeu.'
}
try {
    kubectl --context $Context scale deployment/mecaniqa-iot -n mecaniqa --replicas=2
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao escalar o simulador.' }
    kubectl --context $Context rollout status deployment/mecaniqa-iot -n mecaniqa --timeout=120s
    if ($LASTEXITCODE -ne 0) { throw 'Réplicas indisponíveis.' }
    $tunnel = Open-PrometheusTunnel
    $twoTargets = $false
    for ($attempt = 0; $attempt -lt 45; $attempt++) {
        $targets = Wait-Prometheus
        $ready = @($targets.data.activeTargets | Where-Object { $_.labels.job -eq 'mecaniqa-iot' -and $_.health -eq 'up' })
        if ($ready.Count -eq 2) { $twoTargets = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $twoTargets) { throw 'Descoberta não encontrou duas réplicas saudáveis.' }
    $query = [uri]::EscapeDataString('sum(mecaniqa_iot_readings_total{source="simulator"})')
    $before = Invoke-RestMethod "$baseUrl/api/v1/query?query=$query"
    if ($before.data.result.Count -eq 0) { throw 'Não há séries para testar persistência.' }
    # Consultar o mesmo instante depois do restart prova recuperação do histórico.
    $timestamp = $before.data.result[0].value[0].ToString([Globalization.CultureInfo]::InvariantCulture)
    Stop-Process -Id $tunnel.Id
    $tunnel = $null
    kubectl --context $Context rollout restart deployment/prometheus -n mecaniqa
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao reiniciar Prometheus.' }
    kubectl --context $Context rollout status deployment/prometheus -n mecaniqa --timeout=120s
    if ($LASTEXITCODE -ne 0) { throw 'Prometheus não recuperou.' }
    $tunnel = Open-PrometheusTunnel
    $null = Wait-Prometheus
    $after = Invoke-RestMethod "$baseUrl/api/v1/query?query=$query&time=$timestamp"
    if ($after.data.result.Count -eq 0 -or $before.data.result[0].value[1] -ne $after.data.result[0].value[1]) {
        throw 'Histórico divergiu após restart do Prometheus.'
    }
    kubectl --context $Context rollout restart deployment/mecaniqa-iot -n mecaniqa
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao reiniciar simulador.' }
    kubectl --context $Context rollout status deployment/mecaniqa-iot -n mecaniqa --timeout=120s
    if ($LASTEXITCODE -ne 0) { throw 'Simulador não recuperou.' }
    $report = [ordered]@{ verifiedAt = (Get-Date).ToString('o'); replicasDiscovered = 2; historicalQueryBefore = $before; historicalQueryAfter = $after; simulatorRolloutRecovered = $true; originalReplicas = $originalReplicas }
    $report | ConvertTo-Json -Depth 12 | Set-Content (Join-Path $evidence 'recovery-Kubernetes.json') -Encoding utf8
    Write-Host 'Aprovado: descoberta por réplica, histórico após restart e recuperação do simulador.'
} finally {
    if ($tunnel -and -not $tunnel.HasExited) { Stop-Process -Id $tunnel.Id -ErrorAction SilentlyContinue }
    kubectl --context $Context scale deployment/mecaniqa-iot -n mecaniqa --replicas=$originalReplicas
    if ($LASTEXITCODE -ne 0) { Write-Warning 'Restaure manualmente a quantidade original de réplicas.' }
    Write-Host 'Este teste substituiu Pods. Para demonstrar pelo navegador, reabra os port-forwards nas portas 8000 e 9090 conforme o guia do piloto.'
}
