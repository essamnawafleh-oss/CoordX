; Inno Setup script: wraps dist\CoordX into CoordX-Setup.exe
#define AppVersion GetEnv("COORDX_VERSION")
#if AppVersion == ""
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{6C1E7C52-1F0B-4E57-9F4C-C00D0A1B2C3D}
AppName=CoordX
AppVersion={#AppVersion}
AppPublisher=Essam Nawafleh
DefaultDirName={autopf}\CoordX
DefaultGroupName=CoordX
UninstallDisplayIcon={app}\CoordX.exe
SetupIconFile=assets\icon.ico
OutputDir=Output
OutputBaseFilename=CoordX-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\CoordX\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\CoordX"; Filename: "{app}\CoordX.exe"
Name: "{autodesktop}\CoordX"; Filename: "{app}\CoordX.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\CoordX.exe"; Description: "{cm:LaunchProgram,CoordX}"; Flags: nowait postinstall skipifsilent
