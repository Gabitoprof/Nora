# Starts the ear (whisper-server) and the local voice (Kokoro by default, or Piper) in their own windows.
# With the ElevenLabs voice (cloud), use -Voz nenhuma: only the ear is started.
# Usage, in the repository folder:
#   powershell -ExecutionPolicy Bypass -File scripts\iniciar_voz_windows.ps1
# Then, in another terminal with the environment activated: nora falar --medir
# More accurate ear (download it first with instalar_voz_windows.ps1 -ModeloWhisper large-v3-turbo-q5_0):
#   powershell -ExecutionPolicy Bypass -File scripts\iniciar_voz_windows.ps1 -ModeloWhisper large-v3-turbo-q5_0
# -Feixe 5 tries 5 transcription paths instead of 1 (beam search): fewer errors, slower.

param(
    [string]$ModeloWhisper = "small",
    [ValidateSet("kokoro", "piper", "nenhuma")]
    [string]$Voz = "kokoro",
    [string]$VozPiper = "pt_BR-faber-medium",
    [int]$PortaWhisper = 8178,
    [int]$PortaPiper = 5000,
    [int]$Feixe = 0
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
$argumentos = @(
    "-m", "`"$arquivoModelo`"", "-l", "pt", "-t", $threads, "--host", "127.0.0.1", "--port", $PortaWhisper
)
if ($Feixe -gt 1) { $argumentos += @("-bs", $Feixe) }
Start-Process -FilePath $servidor.FullName -WorkingDirectory $servidor.DirectoryName -ArgumentList $argumentos

# The voices open in a PowerShell window that stays open if the server stops with an error,
# so the message stays visible (before, the window disappeared along with the error).
function Iniciar-Janela([string]$titulo, [string]$comando) {
    $script = "`$Host.UI.RawUI.WindowTitle = '$titulo'; Set-Location '$raiz'; $comando; " +
        "Write-Host ''; Write-Host '$titulo parou. Leia a mensagem acima; feche esta janela quando quiser.'"
    Start-Process -FilePath "powershell" -ArgumentList @("-NoExit", "-Command", $script)
}

if ($Voz -eq "kokoro") {
    Write-Host "Iniciando o Kokoro (porta e voz vêm da config [voz.kokoro])..."
    $nora = Join-Path $raiz ".venv\Scripts\nora.exe"
    if (-not (Test-Path $nora)) { $nora = "nora" }
    Iniciar-Janela "Nora - Kokoro" "& '$nora' servidor-kokoro"
} elseif ($Voz -eq "piper") {
    $modeloPiper = Join-Path $modelos "piper\$VozPiper.onnx"
    if (-not (Test-Path $modeloPiper)) {
        throw "Voz do Piper não encontrada: $modeloPiper (e o .onnx.json ao lado). Confira o nome em -VozPiper."
    }
    Write-Host "Iniciando o Piper na porta $PortaPiper com a voz $VozPiper..."
    $pastaPiper = Join-Path $modelos "piper"
    Iniciar-Janela "Nora - Piper" ("& '$python' -m piper.http_server -m '$VozPiper' --data-dir '$pastaPiper' " +
        "--host 127.0.0.1 --port $PortaPiper")
}

Write-Host "`nJanelas abertas (deixe-as abertas). Espere alguns segundos e rode:"
Write-Host "  nora --verificar"
Write-Host "  nora falar --medir"
