try {
    $Host.UI.RawUI.WindowTitle = "MecaniQA - Teste de Estresse e Escalonamento HPA ao Vivo"
} catch {}

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "   MECANIQA - TESTE DE ESTRESSE, ESCALONAMENTO HPA E ALARMES     " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host ""

$repoRoot = Split-Path -Parent $PSScriptRoot
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

Write-Host "[1/5] Verificando conexao com o Cluster Kubernetes e HPA..." -ForegroundColor Yellow
kubectl get hpa -n mecaniqa
Write-Host ""
kubectl get pods -n mecaniqa -l app=mecaniqa-iot -o wide
Write-Host ""

Write-Host "[2/5] DISPARANDO BOMBARDEIO DE TELEMETRIA IoT (60s / 45 threads)..." -ForegroundColor Magenta
Write-Host "Injetando leituras nos sensores automotivos (validas + erros)..." -ForegroundColor White
Write-Host ""

python "$repoRoot\scripts\stress_generator.py" --url "http://127.0.0.1:8000" --duration 60 --concurrency 45 --error-ratio 0.20

Write-Host ""
Write-Host "[3/5] COLETANDO REACAO DO HPA APOS O PICO DE ESTRESSE..." -ForegroundColor Yellow
Start-Sleep -Seconds 5
kubectl get hpa -n mecaniqa
Write-Host ""
kubectl get pods -n mecaniqa -l app=mecaniqa-iot -o wide
Write-Host ""
kubectl top pods -n mecaniqa
Write-Host ""

Write-Host "[4/5] CONSOLIDANDO EVIDENCIAS DO CLUSTER..." -ForegroundColor Yellow
& "$repoRoot\scripts\capture-evidence.ps1"

Write-Host ""
Write-Host "[5/5] CAPTURANDO PRINTS AUTOMATICOS DO GRAFANA VIA PLAYWRIGHT..." -ForegroundColor Yellow
python "$repoRoot\scripts\take_screenshots.py"

Write-Host ""
Write-Host "=================================================================" -ForegroundColor Green
Write-Host "           DEMONSTRACAO E TESTE CONCLUIDOS COM SUCESSO!          " -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Green
Write-Host "As evidencias e prints foram salvos em: docs/evidencias/ e out/stress-test/" -ForegroundColor White
Write-Host ""
