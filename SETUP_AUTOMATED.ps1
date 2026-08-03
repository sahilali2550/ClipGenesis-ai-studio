# ClipGenesis-Extended Automated Setup (No Manual Intervention)
# This script runs with admin privileges automatically via Task Scheduler

param(
    [string]$Action = "full"
)

# Force admin privileges using scheduled task trick
$scriptPath = $MyInvocation.MyCommand.Path
$taskName = "ClipGenesisSetupElevated"

function Ensure-Elevated {
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Write-Host "Creating scheduled task for elevated execution..."
        $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scriptPath`" -Action `"$Action`""
        $principal = New-ScheduledTaskPrincipal -UserId "BUILTIN\Administrators" -LogonType ServiceAccount -RunLevel Highest
        Register-ScheduledTask -TaskName $taskName -Action $action -Principal $principal -Force | Out-Null
        Start-ScheduledTask -TaskName $taskName
        return
    }
}

# Check admin
Ensure-Elevated
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if ($isAdmin) {
    Set-Location "C:\OpenClaw\.openclaw\.openclaw\workspace\ClipGenesis-Extended"
    
    switch ($Action) {
        "python" {
            Write-Host "=== Installing Python 3.10.11 ==="
            $url = "https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe"
            $installer = "$env:TEMP\python-3.10.11-amd64.exe"
            Invoke-WebRequest -Uri $url -OutFile $installer
            Start-Process -Wait -FilePath $installer -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1", "Include_test=0"
            Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
        }
        
        "requirements" {
            Write-Host "=== Installing ClipGenesis-Extended requirements ==="
            $py = "C:\Users\noree\AppData\Local\Programs\Python\Python312\python.exe"
            & $py -m venv venv
            & .\venv\Scripts\pip.exe install --upgrade pip
            & .\venv\Scripts\pip.exe install -r requirements.txt
            Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
        }
        
        "chatterbox" {
            Write-Host "=== Installing Chatterbox TTS ==="
            & .\venv\Scripts\pip.exe install git+https://github.com/resemble-ai/chatterbox.git
            Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
        }
        
        "full" {
            Write-Host "=== Full Automated Setup ==="
            # Step 1: Python
            Write-Host "Step 1: Python setup..."
            $py = "C:\Users\noree\AppData\Local\Programs\Python\Python312\python.exe"
            
            # Step 2: Venv + requirements
            Write-Host "Step 2: Creating venv..."
            & $py -m venv venv
            
            Write-Host "Step 3: Installing requirements..."
            & .\venv\Scripts\pip.exe install --upgrade pip --break-system-packages
            & .\venv\Scripts\pip.exe install -r requirements.txt --break-system-packages
            
            Write-Host "Step 4: Installing Chatterbox TTS..."
            & .\venv\Scripts\pip.exe install git+https://github.com/resemble-ai/chatterbox.git --break-system-packages
            
            Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
            Write-Host "=== Setup Complete! Run: .\venv\Scripts\activate && python app.py ==="
        }
    }
} else {
    Write-Host "Waiting for elevated task to start..."
    Start-Sleep 5
}