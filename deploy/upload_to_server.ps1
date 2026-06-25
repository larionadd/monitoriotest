param(
    [Parameter(Mandatory = $true)]
    [string]$HostName,

    [Parameter(Mandatory = $false)]
    [string]$User = "ubuntu",

    [Parameter(Mandatory = $false)]
    [int]$Port = 22,

    [Parameter(Mandatory = $false)]
    [string]$IdentityFile = "",

    [Parameter(Mandatory = $false)]
    [string]$RemoteDir = "/tmp/media-monitor-bot-transfer",

    [Parameter(Mandatory = $false)]
    [string]$LocalConfig = "config.json"
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$BackupDir = Join-Path $Root "backup"
$DistDir = Join-Path $Root "dist"
$BackupPath = Join-Path $BackupDir "media_monitor.sqlite3"
$ZipPath = Join-Path $DistDir "media-monitor-bot-server.zip"
$LocalConfigPath = Join-Path $Root $LocalConfig
$TempEnvPath = Join-Path $DistDir "media-monitor-bot.env"
$TempRemoteInstallPath = Join-Path $DistDir "remote_install.sh"

if (-not (Test-Path $Python)) {
    throw "Python venv not found: $Python"
}
if (-not (Test-Path $LocalConfigPath)) {
    throw "Local config not found: $LocalConfigPath"
}

New-Item -ItemType Directory -Force $BackupDir | Out-Null
New-Item -ItemType Directory -Force $DistDir | Out-Null

$Config = Get-Content $LocalConfigPath -Raw -Encoding utf8 | ConvertFrom-Json
$AdminChatIds = ""
if ($Config.admin_chat_ids) {
    $AdminChatIds = ($Config.admin_chat_ids -join ",")
}
$SourceTimeout = if ($Config.source_timeout_seconds) { [int]$Config.source_timeout_seconds } else { 8 }
if ($SourceTimeout -gt 8) {
    $SourceTimeout = 8
}
$RequireOnboarding = if ($Config.require_onboarding) { "true" } else { "false" }
$TrialPlanId = if ($Config.trial_plan_id) { [string]$Config.trial_plan_id } else { "" }
$TrialDays = if ($Config.trial_days) { [int]$Config.trial_days } else { 7 }

$EnvContent = @"
TELEGRAM_BOT_TOKEN=$($Config.telegram_bot_token)
ADMIN_CHAT_IDS=$AdminChatIds
DATABASE_PATH=/var/lib/media-monitor-bot/media_monitor.sqlite3
SOURCES_PATH=/opt/media-monitor-bot/data/sources.csv
SOURCE_TIMEOUT_SECONDS=$SourceTimeout
REQUIRE_ONBOARDING=$RequireOnboarding
TRIAL_PLAN_ID=$TrialPlanId
TRIAL_DAYS=$TrialDays
"@
[System.IO.File]::WriteAllText($TempEnvPath, $EnvContent, [System.Text.UTF8Encoding]::new($false))

& $Python (Join-Path $Root "deploy\backup_sqlite.py") `
    (Join-Path $Root "data\media_monitor.sqlite3") `
    $BackupPath

$Stage = Join-Path $DistDir "package-stage"
if (Test-Path $Stage) {
    Remove-Item -LiteralPath $Stage -Recurse -Force
}
if (Test-Path $ZipPath) {
    Remove-Item -LiteralPath $ZipPath -Force
}
New-Item -ItemType Directory -Force $Stage | Out-Null

$Files = & rg --files $Root | Where-Object {
    $Rel = Resolve-Path $_ -Relative
    $Rel = $Rel.TrimStart(".\")
    $Rel -ne "config.json" -and
    $Rel -notlike "backup\*" -and
    $Rel -notlike "dist\*" -and
    $Rel -notlike "logs\*" -and
    $Rel -notlike "reports\*" -and
    $Rel -notlike "*.sqlite3*" -and
    $Rel -notmatch "(^|[\\/])__pycache__([\\/]|$)" -and
    $Rel -notlike ".venv\*" -and
    $Rel -notlike ".git\*"
}

foreach ($File in $Files) {
    $Rel = Resolve-Path $File -Relative
    $Rel = $Rel.TrimStart(".\")
    $Dest = Join-Path $Stage $Rel
    New-Item -ItemType Directory -Force (Split-Path $Dest -Parent) | Out-Null
    Copy-Item -LiteralPath $File -Destination $Dest -Force
}

Compress-Archive -Path (Join-Path $Stage "*") -DestinationPath $ZipPath -Force
Remove-Item -LiteralPath $Stage -Recurse -Force

$SshTarget = "${User}@${HostName}"
$SshArgs = @("-p", "$Port")
$ScpArgs = @("-P", "$Port")
if ($IdentityFile) {
    $SshArgs += @("-i", $IdentityFile)
    $ScpArgs += @("-i", $IdentityFile)
}

ssh @SshArgs $SshTarget "rm -rf '$RemoteDir' && mkdir -p '$RemoteDir' && chmod 700 '$RemoteDir'"
scp @ScpArgs $ZipPath "${SshTarget}:$RemoteDir/media-monitor-bot-server.zip"
scp @ScpArgs $BackupPath "${SshTarget}:$RemoteDir/media_monitor.sqlite3"
scp @ScpArgs $TempEnvPath "${SshTarget}:$RemoteDir/media-monitor-bot.env"
Remove-Item -LiteralPath $TempEnvPath -Force

$RemoteCommand = @"
set -e
cleanup() {
  cd /
  rm -rf '$RemoteDir'
}
trap cleanup EXIT
cd '$RemoteDir'
chmod 600 media-monitor-bot.env media_monitor.sqlite3
sudo apt-get update
sudo apt-get install -y unzip
rm -rf media-monitor-bot
mkdir media-monitor-bot
unzip -q media-monitor-bot-server.zip -d media-monitor-bot
cd media-monitor-bot
sudo bash deploy/install_server.sh
sudo systemctl stop media-monitor-bot || true
sudo cp '$RemoteDir/media-monitor-bot.env' /etc/media-monitor-bot/media-monitor-bot.env
sudo chown root:media-monitor /etc/media-monitor-bot/media-monitor-bot.env
sudo chmod 640 /etc/media-monitor-bot/media-monitor-bot.env
sudo cp '$RemoteDir/media_monitor.sqlite3' /var/lib/media-monitor-bot/media_monitor.sqlite3
sudo chown media-monitor:media-monitor /var/lib/media-monitor-bot/media_monitor.sqlite3
sudo systemctl restart media-monitor-bot
sudo systemctl --no-pager --full status media-monitor-bot
"@

$RemoteCommand = $RemoteCommand.Replace("`r`n", "`n")
[System.IO.File]::WriteAllText($TempRemoteInstallPath, $RemoteCommand, [System.Text.UTF8Encoding]::new($false))
scp @ScpArgs $TempRemoteInstallPath "${SshTarget}:$RemoteDir/remote_install.sh"
Remove-Item -LiteralPath $TempRemoteInstallPath -Force
ssh @SshArgs $SshTarget "bash '$RemoteDir/remote_install.sh'"

Write-Host "Upload and install completed."
Write-Host "Token/admin env was copied from local $LocalConfig."
