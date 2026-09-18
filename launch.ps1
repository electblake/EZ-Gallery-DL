#Requires -Version 7.0
$ErrorActionPreference = 'Stop'
Start-Process -FilePath "$PSScriptRoot\.venv\Scripts\pythonw.exe" -ArgumentList '-m app' -WorkingDirectory $PSScriptRoot -WindowStyle Normal
