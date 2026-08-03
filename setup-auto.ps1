# ClipGenesis-Extended Auto Setup Script
# Runs with admin privileges automatically

# Check if admin, if not restart as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Restarting as Administrator..."
    Start-Process -FilePath "powershell.exe" -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`"" -Verb RunAs
    exit
}

Set-Location "C:\OpenClaw\.openclaw\.openclaw\workspace\ClipGenesis-Extended"

Write-Host "=== Step 1: Checking Python ==="
$pythonPath = "C:\Users\noree\AppData\Local\Programs\Python\Python312\python.exe"
if (Test-Path $pythonPath) {
    Write-Host "Python 3.12 found"
    & $pythonPath --version
} else {
    Write-Host "Installing Python 3.10.11..."
    $url = "https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe"
    $installer = "$env:TEMP\python-3.10.11-amd64.exe"
    Invoke-WebRequest -Uri $url -OutFile $installer
    Start-Process -Wait -FilePath $installer -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1", "Include_test=0"
}

Write-Host "`n=== Step 2: Creating venv ==="
$py = "C:\Users\noree\AppData\Local\Programs\Python\Python312\python.exe"
& $py -m venv venv

Write-Host "`n=== Step 3: Installing ClipGenesis-Extended requirements ==="
& .\venv\Scripts\pip.exe install --upgrade pip
& .\venv\Scripts\pip.exe install -r requirements.txt

Write-Host "`n=== Step 4: Installing Chatterbox TTS ==="
git clone https://github.com/resemble-ai/chatterbox.git
& .\venv\Scripts\pip.exe install -e .\chatterbox

Write-Host "`n=== Step 5: All requirements installed ==="
Write-Host "To run: .\venv\Scripts\activate && python app.py"