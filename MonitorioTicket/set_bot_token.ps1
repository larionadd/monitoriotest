param(
    [Parameter(Mandatory = $true)]
    [string]$Token
)

$ErrorActionPreference = "Stop"

if ($Token -notmatch '^\d+:[A-Za-z0-9_-]{30,}$') {
    throw "Token format looks invalid. Use the full token from BotFather."
}

if (!(Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

$content = Get-Content ".env" -Raw

if ($content -match '(?m)^TELEGRAM_BOT_TOKEN=') {
    $content = $content -replace '(?m)^TELEGRAM_BOT_TOKEN=.*$', "TELEGRAM_BOT_TOKEN=$Token"
} else {
    $content += "`nTELEGRAM_BOT_TOKEN=$Token`n"
}

if ($content -match '(?m)^RUN_TELEGRAM_BOT=') {
    $content = $content -replace '(?m)^RUN_TELEGRAM_BOT=.*$', "RUN_TELEGRAM_BOT=false"
} else {
    $content += "RUN_TELEGRAM_BOT=false`n"
}

Set-Content ".env" $content -Encoding UTF8
Write-Host "Telegram bot token saved to .env. Start with .\run_bot.ps1 or .\run_all.ps1."
