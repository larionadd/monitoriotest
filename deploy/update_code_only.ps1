param(
    [Parameter(Mandatory = $true)]
    [string]$HostName,

    [Parameter(Mandatory = $false)]
    [string]$User = "root",

    [Parameter(Mandatory = $false)]
    [int]$Port = 22,

    [Parameter(Mandatory = $false)]
    [string]$IdentityFile = "",

    [Parameter(Mandatory = $false)]
    [string]$RemoteDir = "/tmp/media-monitor-bot-code-update"
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$DistDir = Join-Path $Root "dist"
$ZipPath = Join-Path $DistDir "media-monitor-bot-code.zip"
$Stage = Join-Path $DistDir "code-stage"
$RemoteInstallPath = Join-Path $DistDir "remote_code_update.sh"

New-Item -ItemType Directory -Force $DistDir | Out-Null

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
    $Rel -ne "config.international.json" -and
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
scp @ScpArgs $ZipPath "${SshTarget}:$RemoteDir/media-monitor-bot-code.zip"

$RemoteCommand = @"
set -e
cleanup() {
  cd /
  rm -rf '$RemoteDir'
}
trap cleanup EXIT
cd '$RemoteDir'
apt-get update
apt-get install -y unzip
rm -rf media-monitor-bot
mkdir media-monitor-bot
unzip -q media-monitor-bot-code.zip -d media-monitor-bot
cd media-monitor-bot
bash deploy/install_server.sh
systemctl restart media-monitor-bot
systemctl --no-pager --full status media-monitor-bot
"@

$RemoteCommand = $RemoteCommand.Replace("`r`n", "`n")
[System.IO.File]::WriteAllText($RemoteInstallPath, $RemoteCommand, [System.Text.UTF8Encoding]::new($false))
scp @ScpArgs $RemoteInstallPath "${SshTarget}:$RemoteDir/remote_code_update.sh"
Remove-Item -LiteralPath $RemoteInstallPath -Force
ssh @SshArgs $SshTarget "bash '$RemoteDir/remote_code_update.sh'"

Write-Host "Code update completed. Database and env were not uploaded."
