param([string]$BaseUrl = 'http://localhost:8080')
$ErrorActionPreference = "Stop"

function Assert-Equal([string] $Name, $Expected, $Actual) {
    if ($Expected -ne $Actual) {
        throw "$Name esperado '$Expected', recebido '$Actual'"
    }
    Write-Host "PASS $Name"
}

$health = Invoke-WebRequest "$BaseUrl/health" -UseBasicParsing
Assert-Equal "GET /health status" 200 $health.StatusCode
Assert-Equal "GET /health body" '{"service":"mecaniqa-api","status":"UP"}' $health.Content

$root = Invoke-WebRequest "$BaseUrl/" -UseBasicParsing
Assert-Equal "GET / status" 200 $root.StatusCode

try {
    Invoke-WebRequest "$BaseUrl/rota-inexistente" -UseBasicParsing | Out-Null
    throw "GET rota inexistente deveria retornar 404"
} catch {
    if ($_.Exception.Response.StatusCode.value__ -ne 404) { throw }
    Write-Host "PASS GET rota inexistente status"
}

try {
    Invoke-WebRequest "$BaseUrl/health" -Method Post -UseBasicParsing | Out-Null
    throw "POST /health deveria retornar 405"
} catch {
    if ($_.Exception.Response.StatusCode.value__ -ne 405) { throw }
    Write-Host "PASS POST /health status"
}

foreach ($path in @('/healthXYZ', '/health/extra')) {
    try {
        Invoke-WebRequest "$BaseUrl$path" -UseBasicParsing | Out-Null
        throw "GET $path deveria retornar 404"
    } catch {
        if ([int]$_.Exception.Response.StatusCode -ne 404) { throw }
        Write-Host "PASS GET $path status"
    }
}

Write-Host "Smoke test concluído."
