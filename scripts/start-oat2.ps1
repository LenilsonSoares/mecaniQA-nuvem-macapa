[CmdletBinding()]
param(
    [string]$Context = 'docker-desktop',
    [ValidatePattern('^[a-zA-Z0-9_][a-zA-Z0-9_.-]{0,127}$')]
    [string]$ImageTag = ('2.0-' + (Get-Date -Format yyyyMMddHHmmss))
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
    # A imagem local deve estar disponível no runtime do cluster escolhido.
    # Tag única evita que o node reutilize uma versão anterior em cache.
    docker build -t "mecaniqa-iot:$ImageTag" -t mecaniqa-iot:2.0 iot
    if ($LASTEXITCODE -ne 0) { throw 'Falha no build do simulador.' }
    kubectl --context $Context apply -f k8s/oat2/namespace.yaml
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao preparar o namespace.' }
    $rendered = kubectl kustomize k8s/oat2
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao renderizar os manifestos.' }
    $manifest = ($rendered -join [Environment]::NewLine).Replace('image: mecaniqa-iot:2.0', "image: mecaniqa-iot:$ImageTag")
    $manifestPath = Join-Path $repoRoot 'out/oat2-2026-10-07/applied-manifest.yaml'
    New-Item -ItemType Directory -Path (Split-Path $manifestPath) -Force | Out-Null
    $manifest | Set-Content -LiteralPath $manifestPath -Encoding utf8
    kubectl --context $Context apply --dry-run=server -f $manifestPath
    if ($LASTEXITCODE -ne 0) { throw 'Manifestos rejeitados pelo cluster.' }
    kubectl --context $Context apply -f $manifestPath
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao aplicar os recursos.' }
    foreach ($deployment in @('mecaniqa-iot', 'prometheus')) {
        kubectl --context $Context rollout status "deployment/$deployment" -n mecaniqa --timeout=180s
        if ($LASTEXITCODE -ne 0) { throw "Deployment indisponível: $deployment. Confira eventos e disponibilidade da imagem local." }
    }
    kubectl --context $Context get pods,svc,pvc -n mecaniqa
    Write-Host 'Agora execute .\scripts\test-oat2.ps1 para validar a coleta.'
} finally { Pop-Location }
