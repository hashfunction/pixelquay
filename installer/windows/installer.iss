#define ProductName "TintFable"
#define ProductVersion "1.0.1"

; The architecture can be configured on the command line to build the arm64 or x64 installer
#ifndef ProductArch
  #define ProductArch "x64os"
#endif

[Setup]
; Adds option to skip creating start menu entries
AllowNoIcons=yes
AppId=5296E263-5F86-4869-9D59-70D1A8E8A832
AppName={#ProductName}
AppPublisher=Trieflow LLC
AppPublisherURL=https://tintfable.trieflow.com/
AppVerName={#ProductName} {#ProductVersion}
AppVersion={#ProductVersion}
ArchitecturesAllowed={#ProductArch}
ArchitecturesInstallIn64BitMode={#ProductArch}
Compression=lzma2
; Retain the original install path and AppId for upgrade compatibility.
DefaultDirName={autopf}\PixelQuay
DefaultGroupName={#ProductName}
LicenseFile=installer\windows\license.rtf
OutputBaseFilename={#ProductName}
OutputDir=installer\windows
; Allow installing for all users or only the current user
PrivilegesRequiredOverridesAllowed=dialog
SetupIconFile=installer\windows\TintFable.ico
SolidCompression=yes
SourceDir=..\..\
UninstallDisplayIcon={app}\bin\{#ProductName}.exe
WizardSmallImageFile=installer\windows\logo.bmp
WizardStyle=modern

[Icons]
Name: "{group}\{#ProductName}"; Filename: "{app}\bin\{#ProductName}.exe"

[Files]
Source: "release\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Run]
Filename: "{app}\bin\TintFable.exe"; Flags: nowait postinstall skipifsilent; Description: "{cm:LaunchProgram,{#ProductName}}"
