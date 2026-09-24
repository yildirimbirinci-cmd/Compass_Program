$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3.11 -m venv .venv
}

& ".venv\Scripts\python.exe" -m pip install --upgrade pip
& ".venv\Scripts\python.exe" -m pip install -r requirements.txt

if (Test-Path "build") { Remove-Item "build" -Recurse -Force }
if (Test-Path "dist\ArtmachCompass") { Remove-Item "dist\ArtmachCompass" -Recurse -Force }

& ".venv\Scripts\python.exe" -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onedir `
    --name "ArtmachCompass" `
    --icon "resources\icons\ArtmachCompass.ico" `
    --add-data "resources;resources" `
    --add-data "artmach_compass\conversion_engine\blender;artmach_compass\conversion_engine\blender" `
    --add-data "artmach_compass\conversion_engine\maxscripts;artmach_compass\conversion_engine\maxscripts" `
    --add-data "artmach_compass\conversion_engine\config;artmach_compass\conversion_engine\config" `
    --paths "." `
    main.py

Write-Host "Application build complete: dist\ArtmachCompass\ArtmachCompass.exe"

