$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

if (!(Test-Path ".venv")) {
  python -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
& ".\.venv\Scripts\python.exe" -m media_monitor_bot.app --config config.json
