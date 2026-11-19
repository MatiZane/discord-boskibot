$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Tworzenie środowiska .venv i instalowanie zależności..." -ForegroundColor Cyan
    py -m venv .venv
    & ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
    & ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Utworzono plik .env na podstawie .env.example." -ForegroundColor Yellow
    Write-Host "Wpisz w nim DISCORD_TOKEN oraz GEMINI_API_KEY, a następnie uruchom run.ps1 ponownie." -ForegroundColor Yellow
    exit 1
}

& ".\.venv\Scripts\python.exe" main.py
