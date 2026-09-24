$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$InstallDir = Join-Path $env:ProgramFiles "Artmach Compass"
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "Artmach Compass.lnk"

Set-Location $Root
& "$PSScriptRoot\build_windows.ps1"

Get-Process "ArtmachCompass" -ErrorAction SilentlyContinue | Stop-Process -Force

if (Test-Path $InstallDir) {
    Remove-Item $InstallDir -Recurse -Force
}
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
Copy-Item "dist\ArtmachCompass\*" $InstallDir -Recurse -Force

$Exe = Join-Path $InstallDir "ArtmachCompass.exe"
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $Exe
$Shortcut.WorkingDirectory = $InstallDir
$Shortcut.IconLocation = "$Exe,0"
$Shortcut.Description = "Artmach Compass"
$Shortcut.Save()

# Launch through the Windows shell so the application starts in the signed-in
# desktop session instead of inheriting the elevated installer process.
Start-Process -FilePath "$env:WINDIR\explorer.exe" -ArgumentList ('"{0}"' -f $Exe)

$Started = $false
for ($Attempt = 0; $Attempt -lt 20; $Attempt++) {
    Start-Sleep -Milliseconds 500
    if (Get-Process "ArtmachCompass" -ErrorAction SilentlyContinue) {
        $Started = $true
        break
    }
}

if (-not $Started) {
    # Fallback for systems where Explorer does not accept the delegated launch.
    Start-Process -FilePath $Exe -WorkingDirectory $InstallDir
}

Write-Host "Artmach Compass installed and launched. Desktop shortcut: $ShortcutPath"

