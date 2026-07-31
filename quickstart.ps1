$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker is required. Install Docker Desktop, then run this script again."
}
docker compose -f docker-compose.quickstart.yml up --build -d --wait
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
docker compose -f docker-compose.quickstart.yml exec -T sage sage-doctor --url http://127.0.0.1:8080
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host ""
Write-Host "SAGE is ready at http://127.0.0.1:8080"
Write-Host "API docs: http://127.0.0.1:8080/docs"
Write-Host "Try: docker compose -f docker-compose.quickstart.yml exec -T sage sage-demo --url http://127.0.0.1:8080"
