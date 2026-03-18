; Jobber — Windows Installer (Inno Setup)
; Compiled in CI via jrsoftware/innosetup on Wine

#define MyAppName "Jobber"
#define MyAppPublisher "distance1186"
#define MyAppURL "https://github.com/distance1186/jobber"
#define MyAppExeName "jobber-setup.exe"

; Version is injected at build time via /D flag:  iscc /DMyAppVersion=0.1.0
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0-dev"
#endif

[Setup]
AppId={{B7E2F1A3-4D6C-4E8F-9A1B-3C5D7E9F0B2A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
DefaultDirName={autopf}\Jobber
DefaultGroupName={#MyAppName}
LicenseFile=..\..\LICENSE
OutputBaseFilename=jobber-setup-windows-amd64
OutputDir=Output
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
SetupIconFile=compiler:SetupClassicIcon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; Go binary (built in CI, placed next to this .iss before compilation)
Source: "..\..\dist\windows\jobber-setup.exe"; DestDir: "{app}"; Flags: ignoreversion

; Project files needed by docker compose
Source: "..\..\docker-compose.yml"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\db\init.sql"; DestDir: "{app}\db"; Flags: ignoreversion
Source: "..\..\cron\crontab"; DestDir: "{app}\cron"; Flags: ignoreversion
Source: "..\..\.env.example"; DestDir: "{app}"; Flags: ignoreversion

; Agent source (needed for docker compose build)
Source: "..\..\agent\*"; DestDir: "{app}\agent"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Jobber Status"; Filename: "{app}\{#MyAppExeName}"; Parameters: "status --dir ""{app}"""
Name: "{group}\Jobber Config Wizard"; Filename: "{app}\{#MyAppExeName}"; Parameters: "config --dir ""{app}"""
Name: "{group}\Uninstall Jobber"; Filename: "{uninstallexe}"

[Run]
; Post-install: launch the config wizard
Filename: "{app}\{#MyAppExeName}"; Parameters: "install --dir ""{app}"""; \
  Description: "Launch Jobber configuration wizard"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Stop the stack before uninstall
Filename: "{app}\{#MyAppExeName}"; Parameters: "stop --dir ""{app}"""; \
  Flags: runhidden waituntilterminated; RunOnceId: "StopJobber"

[Code]
// Pascal Script — prerequisite checks before installation

function DockerDesktopInstalled: Boolean;
var
  ResultCode: Integer;
begin
  // Check if docker.exe is in PATH
  Result := Exec('cmd.exe', '/C docker version >nul 2>&1', '', SW_HIDE, ewWaitUntilTerminated, ResultCode)
           and (ResultCode = 0);
end;

function WSL2Installed: Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('cmd.exe', '/C wsl --status >nul 2>&1', '', SW_HIDE, ewWaitUntilTerminated, ResultCode)
           and (ResultCode = 0);
end;

function InitializeSetup: Boolean;
var
  Msg: String;
begin
  Result := True;

  // Check WSL2 first (Docker Desktop depends on it)
  if not WSL2Installed then begin
    Msg := 'WSL2 is required but was not detected.' + #13#10 + #13#10 +
           'To install WSL2, open PowerShell as Administrator and run:' + #13#10 +
           '  wsl --install' + #13#10 + #13#10 +
           'After installing WSL2, restart your computer and run this installer again.' + #13#10 + #13#10 +
           'Would you like to continue anyway?';
    if MsgBox(Msg, mbConfirmation, MB_YESNO) = IDNO then begin
      Result := False;
      Exit;
    end;
  end;

  // Check Docker Desktop
  if not DockerDesktopInstalled then begin
    Msg := 'Docker Desktop is required but was not detected.' + #13#10 + #13#10 +
           'Download Docker Desktop from:' + #13#10 +
           '  https://www.docker.com/products/docker-desktop/' + #13#10 + #13#10 +
           'After installing Docker Desktop, ensure it is running and try again.' + #13#10 + #13#10 +
           'Would you like to open the download page now?';
    if MsgBox(Msg, mbConfirmation, MB_YESNO) = IDYES then begin
      ShellExec('open', 'https://www.docker.com/products/docker-desktop/', '', '', SW_SHOWNORMAL, ewNoWait, ResultCode);
    end;
    Result := False;
  end;
end;

var
  ResultCode: Integer;
