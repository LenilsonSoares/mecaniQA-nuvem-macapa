$Host.UI.RawUI.WindowTitle = "MecaniQA - Teste de Estresse e Telemetria IoT"
Clear-Host

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   MECANIQA - DEMONSTRACAO DE ESTRESSE E TELEMETRIA IOT   " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

$repoRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $repoRoot "iot"
$pythonBin = Join-Path $repoRoot "iot\.venv\Scripts\python.exe"
if (-not (Test-Path $pythonBin)) {
    $pythonBin = "python"
}

Write-Host "Iniciando servidor IoT da aplicacao..." -ForegroundColor Yellow
$serverProcess = Start-Process -FilePath $pythonBin -ArgumentList "-m mecaniqa_iot" -PassThru
Start-Sleep -Seconds 2

try {
    Write-Host "[OK] Servidor IoT ativo em http://127.0.0.1:8000" -ForegroundColor Green
    Write-Host "Iniciando bombardeio de requisicoes com telemetria concorrente..." -ForegroundColor Yellow
    Write-Host ""

    $generatorScript = Join-Path $PSScriptRoot "stress_generator.py"
    & $pythonBin $generatorScript --url "http://127.0.0.1:8000" --duration 30 --concurrency 25 --error-ratio 0.20

    Write-Host ""
    Write-Host "==========================================================" -ForegroundColor Cyan
    Write-Host "         TELEMETRIA PROMETHEUS COLETADA DO PROCESSO       " -ForegroundColor Cyan
    Write-Host "==========================================================" -ForegroundColor Cyan
    $metrics = (Invoke-WebRequest "http://127.0.0.1:8000/metrics" -UseBasicParsing).Content
    $lines = $metrics -split "`r?`n"
    $lines | Where-Object { $_ -like '*mecaniqa_iot_readings_total*' -and $_ -notlike '#*' } | ForEach-Object {
        Write-Host "  $_" -ForegroundColor Green
    }
    Write-Host ""
    Write-Host "Teste concluido com sucesso!" -ForegroundColor Cyan
} finally {
    Stop-Process -Id $serverProcess.Id -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Esta janela ficara aberta para voce visualizar ou tirar print." -ForegroundColor Yellow
Write-Host "Pressione qualquer tecla para encerrar..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
