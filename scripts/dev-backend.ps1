# Run from project root via mprocs or directly: .\scripts\dev-backend.ps1
Set-Location "$PSScriptRoot\.."

$pip     = "backend\.venv\Scripts\pip.exe"
$uvicorn = "backend\.venv\Scripts\uvicorn.exe"

# Create venv if it doesn't exist
if (-not (Test-Path $pip)) {
    Write-Host "Creating venv..." -ForegroundColor Yellow
    python -m venv backend\.venv
}

# Always sync requirements (fast if nothing changed, catches partial installs)
Write-Host "Syncing requirements..." -ForegroundColor Cyan
& $pip install -r backend\requirements.txt --quiet

# Wait for postgres
Write-Host "Waiting for database on localhost:5432..." -ForegroundColor Cyan
$retries = 30
$ready = $false
while ($retries -gt 0 -and -not $ready) {
    try {
        $tcp = [System.Net.Sockets.TcpClient]::new("localhost", 5432)
        $tcp.Close()
        $ready = $true
    } catch {
        $retries--
        Start-Sleep -Seconds 1
    }
}

if (-not $ready) {
    Write-Host "Database did not become ready in time. Is Docker running?" -ForegroundColor Red
    exit 1
}

Write-Host "Database ready." -ForegroundColor Green
Set-Location backend
& ".\.venv\Scripts\uvicorn.exe" app.main:app --reload --port 8000
