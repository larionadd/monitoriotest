$ErrorActionPreference = "Stop"

if (!(Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env. Add TELEGRAM_BOT_TOKEN before running the bot."
    exit 1
}

$python = if (Get-Command python -ErrorAction SilentlyContinue) {
    "python"
} elseif (Test-Path "C:\Users\vanil\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe") {
    "C:\Users\vanil\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
} else {
    "py"
}

& $python -m pip install -r requirements.txt
& $python -m app.bot
