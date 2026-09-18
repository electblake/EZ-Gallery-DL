#Requires -Version 7.0
param(
    [string]$IsccPath = "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
)

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
uv venv --python 3.12 --allow-existing build/venv
$buildPython = Join-Path (Get-Location) 'build/venv/Scripts/python.exe'
uv pip sync --python $buildPython scripts/build-requirements.txt
& $buildPython -m unittest discover -s tests -v
& $buildPython -m PyInstaller --clean --noconfirm scripts/app.spec
& $buildPython scripts/stage-licenses.py
& $buildPython scripts/check-bundle.py
$version = & $buildPython -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])'
& $IsccPath "/DAppVersion=$version" scripts/installer.iss
Get-Item "dist/EZ-Gallery-DL-$version-windows-x64-Setup.exe"
