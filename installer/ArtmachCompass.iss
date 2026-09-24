#define MyAppName "Artmach Compass"
#define MyAppVersion "0.6.4"
#define MyAppPublisher "Artmach"
#define MyAppExeName "ArtmachCompass.exe"

[Setup]
AppId={{92E072CA-3E15-4CB3-B702-9926896D2F76}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Artmach Compass
DefaultGroupName=Artmach Compass
DisableProgramGroupPage=yes
PrivilegesRequired=admin
OutputDir=..\dist_installer
OutputBaseFilename=Artmach_Compass_Setup_{#MyAppVersion}
SetupIconFile=..\resources\icons\ArtmachCompass.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no

[Files]
Source: "..\dist\ArtmachCompass\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autodesktop}\Artmach Compass"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\Artmach Compass"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\Uninstall Artmach Compass"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Artmach Compass"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
