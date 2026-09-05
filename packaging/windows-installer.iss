#define AppName "YomiPalette"
#define AppVersion GetEnv("APP_VERSION")
#define AppExeName "YomiPalette.exe"

[Setup]
AppId={{B7D2B4A6-5C28-4E14-9B78-5C5F2A8D9B10}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=YomiPalette
DefaultDirName={autopf}\YomiPalette
; Keep the previous installation directory for existing users.
UsePreviousAppDir=yes
DefaultGroupName={#AppName}
OutputDir=..\release
OutputBaseFilename=YomiPalette_Setup_{#AppVersion}
SetupIconFile=..\assets\app-icon.ico
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#AppExeName}

; Remove only known legacy app files and shortcuts during an upgrade.
[InstallDelete]
Type: files; Name: "{app}\TTS-Text-MP3.exe"
Type: files; Name: "{autoprograms}\TTS Text to MP3.lnk"
Type: files; Name: "{autodesktop}\TTS Text to MP3.lnk"

[Files]
Source: "..\dist\YomiPalette\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{#AppName}を起動"; Flags: postinstall nowait skipifsilent
