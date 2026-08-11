$ErrorActionPreference = "Stop"

if (!(Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

$python = if (Get-Command python -ErrorAction SilentlyContinue) {
    (Get-Command python).Source
} elseif (Test-Path "C:\Users\vanil\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe") {
    "C:\Users\vanil\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
} else {
    (Get-Command py).Source
}

& $python -m pip install -r requirements.txt

$webLog = Join-Path (Get-Location) "uvicorn.log"
$webErr = Join-Path (Get-Location) "uvicorn.err.log"
Start-Process -FilePath $python -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8017") -WorkingDirectory (Get-Location) -RedirectStandardOutput $webLog -RedirectStandardError $webErr -WindowStyle Hidden

$envContent = Get-Content ".env" -Raw
if ($envContent -match "TELEGRAM_BOT_TOKEN=\S+") {
    $botLog = Join-Path (Get-Location) "bot.log"
    $botErr = Join-Path (Get-Location) "bot.err.log"
    Start-Process -FilePath $python -ArgumentList @("-m", "app.bot") -WorkingDirectory (Get-Location) -RedirectStandardOutput $botLog -RedirectStandardError $botErr -WindowStyle Hidden
    Write-Host "Cabinet and bot started."
} else {
    Write-Host "Cabinet started. Bot not started because TELEGRAM_BOT_TOKEN is empty."
}

Write-Host "Cabinet: http://127.0.0.1:8017"
