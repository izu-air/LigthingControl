$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonw = Join-Path $root ".venv\Scripts\pythonw.exe"
$app = Join-Path $root "app.py"
$icon = Join-Path $root "assets\icon.ico"

if (-not (Test-Path $pythonw)) {
    Write-Host "Не найден $pythonw"
    Write-Host "Сначала создай виртуальное окружение по инструкции в README.md (python -m venv .venv ...)"
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
$shortcut.Description = "LigthingControl - управление лампочкой и RGB-лентой"
$shortcut.Save()

Write-Host "Готово! Ярлык создан на рабочем столе: $shortcutPath"
