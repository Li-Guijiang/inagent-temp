#define MyAppName "命题188智能制造演示包"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "命题188智能制造项目组"
#define MyAppExeName "SmartManufacturingDemo.exe"

[Setup]
AppId={{B8B1C8E0-3F6A-4FA3-A938-188SM2026DEMO}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\SmartManufacturingDemo
DefaultGroupName={#MyAppName}
OutputDir=installer-output
OutputBaseFilename=SmartManufacturingDemo-Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=

[Files]
Source: "dist\SmartManufacturingDemo\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autodesktop}\命题188智能制造演示包"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\命题188智能制造演示包"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\卸载命题188智能制造演示包"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动智能制造演示包"; Flags: nowait postinstall skipifsilent
