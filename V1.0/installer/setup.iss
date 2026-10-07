; Inno Setup script for Part Number Manager
; Build (adjust ISCC path to your machine):
;   ISCC.exe setup.iss
;   e.g. "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" setup.iss
;
; Default install directory is a folder under D:\Program Files.
; The wizard lets the user pick any other directory and creates the folder/files there.
;
; NOTE (open-source): run this from the installer/ folder, and first build the exe
; (PyInstaller) so that ..\source\dist\PartNumberManager.exe exists. Paths below are
; relative to this file's directory.

#define MyAppName "Part Number Manager"
#define MyAppVersion "3.1.0"
#define MyAppPublisher "PN Manager"
#define MyAppExeName "PartNumberManager.exe"

[Setup]
AppId={{8F3C0E2A-5B4D-4C67-9A21-4D2E8F0B1C63}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
; Default install directory: a folder under D:\Program Files.
DefaultDirName=D:\Program Files\PartNumber Manager
; Always show the "Choose Install Location" page so the user can pick a custom path.
DisableDirPage=no
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=PartNumberManagerSetup
SetupIconFile=..\build_assets\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Admin rights are required to create the install folder/files under D:\Program Files.
PrivilegesRequired=admin
RestartIfNeededByRun=no
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "..\source\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
