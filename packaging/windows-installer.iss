#define AppName "TTS Text to MP3"
#define AppVersion GetEnv("APP_VERSION")
#define AppExeName "TTS-Text-MP3.exe"

[Setup]
AppId={{B7D2B4A6-5C28-4E14-9B78-5C5F2A8D9B10}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=TTS Text to MP3
DefaultDirName={autopf}\TTS Text to MP3
DefaultGroupName={#AppName}
OutputDir=..\release
OutputBaseFilename=TTS-Text-MP3_Setup_{#AppVersion}
SetupIconFile=..\assets\app-icon.ico
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#AppExeName}

[Files]
Source: "..\dist\TTS-Text-MP3\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{#AppName}を起動"; Flags: postinstall nowait skipifsilent
