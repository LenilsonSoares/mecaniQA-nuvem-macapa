[CmdletBinding()]
param(
    [string]$BaseUrl = 'http://127.0.0.1:8000',
    [int]$DurationSeconds = 60,
    [int]$Concurrency = 30,
    [double]$ErrorRatio = 0.15
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Host "=== MecaniQA - Teste de Estresse IoT ===" -ForegroundColor Cyan
Write-Host "Verificando conectividade com $BaseUrl/health..."

try {
    $health = Invoke-RestMethod "$BaseUrl/health" -TimeoutSec 5
    Write-Host "API IoT conectada com sucesso (status: $($health.status))." -ForegroundColor Green
} catch {
    Write-Error "Nao foi possivel conectar em $BaseUrl/health. Verifique se o container ou port-forward esta ativo."
    return
}

# Python runner (prioriza venv do repositorio)
$pythonBin = Join-Path $repoRoot "iot\.venv\Scripts\python.exe"
if (-not (Test-Path $pythonBin)) {
    $pythonBin = "python"
}

$generatorScript = Join-Path $PSScriptRoot "stress_generator.py"

Write-Host "`nDisparando injecao de carga..." -ForegroundColor Yellow
& $pythonBin $generatorScript --url $BaseUrl --duration $DurationSeconds --concurrency $Concurrency --error-ratio $ErrorRatio

Write-Host "`nColetando metricas pos-estresse..." -ForegroundColor Cyan
try {
    $metrics = (Invoke-WebRequest "$BaseUrl/metrics" -UseBasicParsing).Content
    $lines = $metrics -split "`r?`n"
    $successLine = ($lines | Where-Object { $_ -like '*mecaniqa_iot_readings_total*result="success"*source="http"*' }) -join ""
    $errorLine = ($lines | Where-Object { $_ -like '*mecaniqa_iot_readings_total*result="error"*source="http"*' }) -join ""

    Write-Host "Metricas acumuladas no endpoint:" -ForegroundColor White
    Write-Host "  $successLine" -ForegroundColor Green
    Write-Host "  $errorLine" -ForegroundColor Yellow
} catch {
    Write-Warning "Nao foi possivel coletar metricas pos-teste."
}

Write-Host "`nTeste de estresse finalizado com sucesso." -ForegroundColor Green
