; Nora's installer (Inno Setup 6). Built by scripts\empacotar_windows.ps1, which passes
; /DVersao and /DCommit. Installs without asking for admin, in the user folder. The personal config
; and the memory live in %APPDATA%\Nora and are NOT deleted on uninstall.
; No digital signature for now: Windows warns the first time (docs\INSTALACAO.md).

#ifndef Versao
  #define Versao "0.0.0-dev"
#endif
#ifndef Commit
  #define Commit "desconhecido"
#endif

[Setup]
AppId={{8238C798-682D-404A-80FF-9E1282A03998}
AppName=Nora
AppVersion={#Versao}
AppVerName=Nora {#Versao} ({#Commit})
AppPublisher=Carlos Gabriel Moura Santiago
DefaultDirName={localappdata}\Programs\Nora
DefaultGroupName=Nora
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=Nora-{#Versao}-instalador
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\LICENSE
UninstallDisplayName=Nora {#Versao}
CloseApplications=yes

[Languages]
Name: "pt"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "dependencias"; Description: "Instalar agora o pacote de dependências (Ollama, modelos, whisper.cpp; precisa de internet e alguns GB)"
Name: "areadetrabalho"; Description: "Criar atalho da Nora na área de trabalho"; Flags: unchecked

[Files]
Source: "..\dist\nora\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\Nora"; Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\iniciar_nora.ps1"""; WorkingDir: "{app}"; Comment: "Abre a Nora com a HUD e a escuta contínua"
Name: "{group}\Nora - verificar instalação"; Filename: "{cmd}"; Parameters: "/k """"{app}\nora.exe"" --verificar"""; WorkingDir: "{app}"
Name: "{group}\Instalar dependências da Nora"; Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\instalar_dependencias.ps1"""; WorkingDir: "{app}"
Name: "{group}\Pasta da Nora (config e memória)"; Filename: "{userappdata}\Nora"
Name: "{group}\Guia de instalação"; Filename: "{app}\INSTALACAO.md"
Name: "{autodesktop}\Nora"; Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\iniciar_nora.ps1"""; WorkingDir: "{app}"; Tasks: areadetrabalho

[Run]
Filename: "{app}\nora.exe"; Parameters: "--verificar"; Flags: runhidden waituntilterminated; StatusMsg: "Preparando a pasta da Nora..."
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\instalar_dependencias.ps1"""; Tasks: dependencias; Flags: waituntilterminated; StatusMsg: "Instalando o pacote de dependências..."
