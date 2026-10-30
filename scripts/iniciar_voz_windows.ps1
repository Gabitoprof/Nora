# Inicia o ouvido (whisper-server) e a voz (Piper) em janelas próprias.
# Uso, na pasta do repositório:
#   powershell -ExecutionPolicy Bypass -File scripts\iniciar_voz_windows.ps1
# Depois, em outro terminal com o ambiente ativado: ella falar --medir

param(
    [string]$ModeloWhisper = "small",
    [string]$Voz = "pt_BR-faber-medium",
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

Write-Host "Iniciando o Piper na porta $PortaPiper com a voz $Voz..."
Start-Process -FilePath $python -ArgumentList @(
    "-m", "piper.http_server", "-m", $Voz, "--data-dir", "`"$(Join-Path $modelos 'piper')`"",
    "--host", "127.0.0.1", "--port", $PortaPiper
)

Write-Host "`nDuas janelas abriram (deixe-as abertas). Espere alguns segundos e rode:"
Write-Host "  ella --verificar"
Write-Host "  ella falar --medir"
