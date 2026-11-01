# Inicia o ouvido (whisper-server) e a voz local (Kokoro por padrão, ou Piper) em janelas próprias.
# Com a voz do ElevenLabs (nuvem), use -Voz nenhuma: só o ouvido é iniciado.
# Uso, na pasta do repositório:
#   powershell -ExecutionPolicy Bypass -File scripts\iniciar_voz_windows.ps1
# Depois, em outro terminal com o ambiente ativado: nora falar --medir

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

# As vozes abrem numa janela do PowerShell que continua aberta se o servidor parar com erro,
# para a mensagem ficar visível (antes a janela sumia junto com o erro).
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
