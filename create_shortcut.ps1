$desktop = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktop "ClipGenesis AI Studio.lnk"
$wshell = New-Object -ComObject WScript.Shell
$shortcut = $wshell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = Join-Path $PSScriptRoot "run_webui.bat"
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.Description = "ClipGenesis AI Video & Voice Studio"
$shortcut.IconLocation = "shell32.dll,137"
$shortcut.Save()
Write-Host "Desktop Shortcut Created: $shortcutPath"
