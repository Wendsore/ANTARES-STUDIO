; Installateur Windows d'ANTARES Studio (Inno Setup 6), construit à partir de « dist\ANTARES Studio ».
;
; Usage (Windows, depuis la racine du dépôt, après « python packaging/build.py ») :
;   iscc /DAppVersion=0.1.0 packaging\installer.iss
; Produit « dist\installer\ANTARES-Studio-<version>-setup.exe ».
;
; Choix (ADR-0006) : installation pour l'utilisateur courant par défaut, sans droits d'administrateur
; (proposition « pour tous les utilisateurs » dans l'assistant) ; raccourci du menu Démarrer, icône de
; bureau facultative ; la désinstallation laisse intacts les projets et les préférences.
; Signature de code : NON faite — elle exige un certificat de signature acheté par l'éditeur. Sans
; signature, Windows SmartScreen affiche « Éditeur inconnu » à la première exécution.

#ifndef AppVersion
  #define AppVersion "0.0.0-dev"
#endif
#define AppName "ANTARES Studio"
#define AppExe "ANTARES Studio.exe"
#define SourceDir "..\dist\ANTARES Studio"

[Setup]
AppId={{5B7F0E36-2F1B-4E52-9C1A-6D1E2A0B7A11}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Wendsore
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
OutputDir=..\dist\installer
OutputBaseFilename=ANTARES-Studio-{#AppVersion}-setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
InfoBeforeFile=..\packaging\THIRD_PARTY_NOTICES.md

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
