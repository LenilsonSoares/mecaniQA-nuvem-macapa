$ErrorActionPreference = "Stop"

function Assert-Equal([string] $Name, $Expected, $Actual) {
    if ($Expected -ne $Actual) {
        throw "$Name esperado '$Expected', recebido '$Actual'"
    }
    Write-Host "PASS $Name"
}

$health = Invoke-WebRequest "http://localhost:8080/health" -UseBasicParsing
Assert-Equal "GET /health status" 200 $health.StatusCode
Assert-Equal "GET /health body" '{"service":"mecaniqa-api","status":"UP"}' $health.Content

$root = Invoke-WebRequest "http://localhost:8080/" -UseBasicParsing
Assert-Equal "GET / status" 200 $root.StatusCode

try {
    Invoke-WebRequest "http://localhost:8080/rota-inexistente" -UseBasicParsing | Out-Null
    throw "GET rota inexistente deveria retornar 404"
} catch {
    if ($_.Exception.Response.StatusCode.value__ -ne 404) { throw }
    Write-Host "PASS GET rota inexistente status"
}

try {
    Invoke-WebRequest "http://localhost:8080/health" -Method Post -UseBasicParsing | Out-Null
    throw "POST /health deveria retornar 405"
} catch {
    if ($_.Exception.Response.StatusCode.value__ -ne 405) { throw }
    Write-Host "PASS POST /health status"
}

Write-Host "Smoke test concluído."
