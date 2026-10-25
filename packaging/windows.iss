; Inno Setup script for the Windows installer.
; Installs per user (no admin rights, no Python): a legal tool does not belong in the system folder.
; Saved as UTF-8 with BOM: without it the compiler reads the umlauts as ANSI.

#define Name "AI Act Compliance Helper"
#define Version "2.0.0"
#define Publisher "Daniel Hütte"
#define ExeName "ComplianceHelper.exe"

[Setup]
AppId={{7B3A1E52-9C44-4C7E-9E2E-0D6E1A4C8F31}
AppName={cm:AppTitle}
AppVersion={#Version}
AppPublisher={#Publisher}
DefaultDirName={autopf}\ComplianceHelper
DefaultGroupName={cm:AppTitle}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=output
OutputBaseFilename=ComplianceHelper-Windows-Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[CustomMessages]
english.AppTitle=AI Act Compliance Helper
german.AppTitle=Konformitätshelfer
english.DesktopIcon=Create a desktop icon
german.DesktopIcon=Symbol auf dem Schreibtisch anlegen
english.AdditionalTasks=Additional tasks:
german.AdditionalTasks=Zusätzliche Aufgaben:
english.LaunchNow=Start the AI Act Compliance Helper now
german.LaunchNow=Konformitätshelfer jetzt starten

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopIcon}"; \
  GroupDescription: "{cm:AdditionalTasks}"; Flags: unchecked

[Files]
Source: "..\dist\ComplianceHelper\*"; DestDir: "{app}"; \
  Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{cm:AppTitle}"; Filename: "{app}\{#ExeName}"
Name: "{autodesktop}\{cm:AppTitle}"; Filename: "{app}\{#ExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#ExeName}"; Description: "{cm:LaunchNow}"; \
  Flags: nowait postinstall skipifsilent
