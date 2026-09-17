$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonw = Join-Path $root ".venv\Scripts\pythonw.exe"
$app = Join-Path $root "app.py"
$icon = Join-Path $root "assets\icon.ico"

if (-not (Test-Path $pythonw)) {
    Write-Host "Not found: $pythonw"
    Write-Host "Create the virtual environment first (see README.md: python -m venv .venv ...)"
    exit 1
}

$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "LigthingControl.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonw
$shortcut.Arguments = '"' + $app + '"'
$shortcut.WorkingDirectory = $root
if (Test-Path $icon) {
    $shortcut.IconLocation = $icon
}
$shortcut.Description = "LigthingControl - lamp and RGB strip control"
$shortcut.Save()

Write-Host "Done! Shortcut created on the Desktop: $shortcutPath"
