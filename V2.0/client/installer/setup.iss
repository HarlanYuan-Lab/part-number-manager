; Inno Setup script for Part Number Manager V2 (central PostgreSQL client)
; Build (adjust ISCC path to your machine):
;   ISCC.exe setup.iss
;   e.g. "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" setup.iss
;
; Default install directory is a folder under D:\Program Files.
; The wizard lets the user pick any other directory and creates the folder there.
;
; NOTE (open-source): run this from the client/ folder, and first build the exe
; (PyInstaller) so that dist\PartNumberManagerV2.exe exists. Paths below are
; relative to this file's directory.

#define MyAppName "Part Number Manager V2"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "PN Manager"
#define MyAppExeName "PartNumberManagerV2.exe"

[Setup]
AppId={{A6F9D3C4-8E2B-4B7A-9C41-5F8D2E7A9B04}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName=D:\Program Files\Part Number Manager V2
DisableDirPage=no
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=PartNumberManagerV2Setup
SetupIconFile=..\build_assets\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
RestartIfNeededByRun=no
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
