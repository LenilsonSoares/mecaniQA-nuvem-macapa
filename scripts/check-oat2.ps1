[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
    docker build -f iot/Dockerfile.test -t mecaniqa-iot-test:2.0 iot
    if ($LASTEXITCODE -ne 0) { throw 'Falha no build de testes.' }
    docker run --rm mecaniqa-iot-test:2.0 ruff check .
    if ($LASTEXITCODE -ne 0) { throw 'Falha na análise estática.' }
    docker run --rm mecaniqa-iot-test:2.0 ruff format --check .
    if ($LASTEXITCODE -ne 0) { throw 'Formatação inconsistente.' }
    docker run --rm mecaniqa-iot-test:2.0
    if ($LASTEXITCODE -ne 0) { throw 'Falha nos testes Python.' }
    foreach ($config in @('k8s/oat2/prometheus.yml', 'monitoring/prometheus-local.yml')) {
        $configPath = Join-Path $repoRoot $config
        docker run --rm --entrypoint /bin/promtool --mount "type=bind,source=$configPath,target=/etc/prometheus/check.yml,readonly" prom/prometheus:v3.15.0 check config --syntax-only /etc/prometheus/check.yml
        if ($LASTEXITCODE -ne 0) { throw "Configuração inválida: $config" }
    }
    docker compose -f docker-compose.oat2.yml config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Compose inválido.' }
    Write-Host 'Código, testes e configurações da OAT 2 aprovados.'
} finally { Pop-Location }
