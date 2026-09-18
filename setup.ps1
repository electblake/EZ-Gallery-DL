#Requires -Version 7.0
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
Set-Location -LiteralPath $PSScriptRoot
uv sync --python 3.12
$shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $PSScriptRoot 'EZ Gallery DL.lnk'))
$shortcut.TargetPath = Join-Path $PSScriptRoot '.venv\Scripts\pythonw.exe'
$shortcut.Arguments = '-m app'
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.Description = 'Run EZ Gallery DL'
$shortcut.Save()
