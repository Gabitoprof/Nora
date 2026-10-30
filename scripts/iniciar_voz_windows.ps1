# Inicia o ouvido (whisper-server) e a voz local (Kokoro por padrão, ou Piper) em janelas próprias.
# Com a voz do ElevenLabs (nuvem), use -Voz nenhuma: só o ouvido é iniciado.
# Uso, na pasta do repositório:
#   powershell -ExecutionPolicy Bypass -File scripts\iniciar_voz_windows.ps1
# Depois, em outro terminal com o ambiente ativado: ella falar --medir

param(
    [string]$ModeloWhisper = "small",
    [ValidateSet("kokoro", "piper", "nenhuma")]
    [string]$Voz = "kokoro",
    [string]$VozPiper = "pt_BR-faber-medium",
    [int]$PortaWhisper = 8178,
    [int]$PortaPiper = 5000
)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$modelos = Join-Path $raiz "models"
$python = Join-Path $raiz ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

$servidor = Get-ChildItem -Path (Join-Path $raiz "ferramentas\whisper") -Recurse -Filter "whisper-server.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $servidor) { throw "whisper-server.exe não encontrado. Rode antes scripts\instalar_voz_windows.ps1" }
$arquivoModelo = Join-Path $modelos "ggml-$ModeloWhisper.bin"
if (-not (Test-Path $arquivoModelo)) { throw "Modelo $arquivoModelo não encontrado. Rode antes scripts\instalar_voz_windows.ps1" }

$threads = [Math]::Max(1, [Environment]::ProcessorCount - 2)
Write-Host "Iniciando o whisper-server na porta $PortaWhisper ($threads threads)..."
Start-Process -FilePath $servidor.FullName -WorkingDirectory $servidor.DirectoryName -ArgumentList @(
    "-m", "`"$arquivoModelo`"", "-l", "pt", "-t", $threads, "--host", "127.0.0.1", "--port", $PortaWhisper
)

if ($Voz -eq "kokoro") {
    Write-Host "Iniciando o Kokoro (porta e voz vêm da config [voz.kokoro])..."
    $ella = Join-Path $raiz ".venv\Scripts\ella.exe"
    if (-not (Test-Path $ella)) { $ella = "ella" }
    Start-Process -FilePath $ella -WorkingDirectory $raiz -ArgumentList @("servidor-kokoro")
} elseif ($Voz -eq "piper") {
    Write-Host "Iniciando o Piper na porta $PortaPiper com a voz $VozPiper..."
    Start-Process -FilePath $python -ArgumentList @(
        "-m", "piper.http_server", "-m", $VozPiper, "--data-dir", "`"$(Join-Path $modelos 'piper')`"",
        "--host", "127.0.0.1", "--port", $PortaPiper
    )
}

Write-Host "`nJanelas abertas (deixe-as abertas). Espere alguns segundos e rode:"
Write-Host "  ella --verificar"
Write-Host "  ella falar --medir"
