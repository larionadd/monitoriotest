$ErrorActionPreference = "Stop"

if (!(Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

$python = if (Get-Command python -ErrorAction SilentlyContinue) {
    "python"
} elseif (Test-Path "C:\Users\vanil\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe") {
    "C:\Users\vanil\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
} else {
    "py"
}

& $python -m pip install -r requirements.txt
& $python -m uvicorn app.main:app --host 127.0.0.1 --port 8017 --reload
