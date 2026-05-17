# Run from project root via mprocs or directly: .\scripts\dev-frontend.ps1
Set-Location "$PSScriptRoot\..\frontend"

if (-not (Test-Path "node_modules")) {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    pnpm install
}

pnpm dev
