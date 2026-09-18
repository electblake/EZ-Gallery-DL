#define AppName "EZ Gallery DL"

[Setup]
AppId=EZ-Gallery-DL.Desktop
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\EZ-Gallery-DL
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=EZ-Gallery-DL-{#AppVersion}-windows-x64-Setup
UninstallDisplayIcon={app}\EZ-Gallery-DL.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Files]
Source: "..\dist\EZ-Gallery-DL\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\EZ-Gallery-DL.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\EZ-Gallery-DL.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\EZ-Gallery-DL.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
