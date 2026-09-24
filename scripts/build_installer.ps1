$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

& "$PSScriptRoot\build_windows.ps1"

$Candidates = @(
    "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)
$ISCC = $Candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $ISCC) {
    throw "Inno Setup 6 was not found. Install it, then run this script again."
}

& $ISCC "installer\ArtmachCompass.iss"
Write-Host "Installer complete: dist_installer\Artmach_Compass_Setup_0.6.1.exe"
