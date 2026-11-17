#ifndef AppVersion
  #error AppVersion is required
#endif
#ifndef BundleDir
  #error BundleDir is required
#endif

[Setup]
AppId={{400F60D3-F378-465A-9E76-4C1F12DF7C10}
AppName=PDF Toolbox
AppVersion={#AppVersion}
AppVerName=PDF Toolbox {#AppVersion}
DefaultDirName={localappdata}\Programs\PDF Toolbox
DefaultGroupName=PDF Toolbox
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
DisableWelcomePage=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
Compression=lzma2
SolidCompression=yes
OutputDir=..\dist
OutputBaseFilename=PDF-Toolbox-Setup-x64
UninstallDisplayIcon={app}\PDF Toolbox.exe
WizardStyle=modern
SetupIconFile=..\resources\pdf-toolbox.ico
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\PDF Toolbox"; Filename: "{app}\PDF Toolbox.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\PDF Toolbox"; Filename: "{app}\PDF Toolbox.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\PDF Toolbox.exe"; WorkingDir: "{app}"; Description: "Launch PDF Toolbox"; Flags: nowait postinstall skipifsilent

[Code]
var
  PreviousFiles: TArrayOfString;

function GetFileAttributes(FileName: String): LongWord;
  external 'GetFileAttributesW@kernel32.dll stdcall';

function OwnedRuntimeFile(const Relative: String): Boolean;
var
  Candidate, Root, Extension: String;
  Attributes: LongWord;
begin
  Result := False;
  if (Pos('_internal\', Relative) <> 1) or (Pos('..', Relative) > 0) or
     (Pos(':', Relative) > 0) or (Pos('/', Relative) > 0) then Exit;
  Extension := Lowercase(ExtractFileExt(Relative));
  if (Extension <> '.dll') and (Extension <> '.pyd') and (Extension <> '.qm') then Exit;
  Root := ExpandConstant('{app}');
  Candidate := AddBackslash(Root) + Relative;
  while CompareText(Candidate, Root) <> 0 do begin
    Attributes := GetFileAttributes(Candidate);
    if (Attributes = $FFFFFFFF) or ((Attributes and $400) <> 0) then Exit;
    Candidate := ExtractFileDir(Candidate);
  end;
  Attributes := GetFileAttributes(Root);
  Result := (Attributes <> $FFFFFFFF) and ((Attributes and $400) = 0);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  CurrentFiles: TArrayOfString;
  I, J: Integer;
  ExistsInNewBundle: Boolean;
  Root, Inventory: String;
begin
  Root := ExpandConstant('{app}');
  Inventory := AddBackslash(Root) + '.bundle-files.txt';
  if CurStep = ssInstall then begin
    LoadStringsFromFile(Inventory, PreviousFiles);
  end else if CurStep = ssPostInstall then begin
    if not LoadStringsFromFile(Inventory, CurrentFiles) then Exit;
    for I := 0 to GetArrayLength(PreviousFiles) - 1 do begin
      ExistsInNewBundle := False;
      for J := 0 to GetArrayLength(CurrentFiles) - 1 do
        if CompareText(PreviousFiles[I], CurrentFiles[J]) = 0 then begin
          ExistsInNewBundle := True;
          Break;
        end;
      if (not ExistsInNewBundle) and OwnedRuntimeFile(PreviousFiles[I]) then
        DeleteFile(AddBackslash(Root) + PreviousFiles[I]);
    end;
  end;
end;

function OpenProcess(Access: LongWord; Inherit: Boolean; PID: LongWord): THandle;
  external 'OpenProcess@kernel32.dll stdcall';
function WaitForSingleObject(Handle: THandle; Milliseconds: LongWord): LongWord;
  external 'WaitForSingleObject@kernel32.dll stdcall';
function CloseHandle(Handle: THandle): Boolean;
  external 'CloseHandle@kernel32.dll stdcall';

function InitializeSetup(): Boolean;
var
  PID: Integer;
  Handle: THandle;
begin
  Result := True;
  PID := StrToIntDef(ExpandConstant('{param:WAITPID|0}'), 0);
  if PID <= 0 then Exit;
  Handle := OpenProcess($00100000, False, PID);
  if Handle = 0 then Exit;
  Result := WaitForSingleObject(Handle, 15000) = 0;
  CloseHandle(Handle);
  if not Result then
    MsgBox('Close PDF Toolbox and start the installer again.', mbError, MB_OK);
end;
