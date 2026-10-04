#define MyAppName "NetScope"
#define MyAppVersion "1.0.0"
[Setup]
AppId={{176919D5-A8BA-4312-832A-8CA7F345BA18}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\NetScope
DefaultGroupName=NetScope
AppPublisher=mnerst1
AppPublisherURL=https://github.com/mnerst1/NetScope
AppSupportURL=https://github.com/mnerst1/NetScope/issues
PrivilegesRequired=lowest
OutputDir=release
OutputBaseFilename=NetScope-Setup-v1.0.0
SetupIconFile=netscope\assets\netscope.ico
UninstallDisplayIcon={app}\NetScope.exe
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
[CustomMessages]
english.DesktopIcon=Create a desktop shortcut
russian.DesktopIcon=Создать ярлык на рабочем столе
[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopIcon}"; Flags: unchecked
[Files]
Source: "dist\NetScope\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\NetScope"; Filename: "{app}\NetScope.exe"
Name: "{autodesktop}\NetScope"; Filename: "{app}\NetScope.exe"; Tasks: desktopicon
[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueName: "NetScope"; Flags: uninsdeletevalue
