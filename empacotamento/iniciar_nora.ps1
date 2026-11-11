# Opens the installed Nora: starts Ollama and the ear (whisper-server) if they are not running yet,
# opens the HUD in the browser and starts continuous listening (nora ouvir --hud). Shortcut: Start menu > Nora.

param([int]$PortaHud = 8765, [int]$PortaWhisper = 8178)

$ErrorActionPreference = "Stop"
$programa = $PSScriptRoot
$pasta = if ($env:NORA_HOME) { $env:NORA_HOME } else { Join-Path $env:APPDATA "Nora" }
function Responde([int]$porta) {
    $cliente = New-Object Net.Sockets.TcpClient
    try { $cliente.Connect("127.0.0.1", $porta); return $true } catch { return $false } finally { $cliente.Close() }
}

if (-not (Responde 11434)) {
    $ollama = Get-Command ollama -ErrorAction SilentlyContinue
    $ollama = if ($ollama) { $ollama.Source } else { Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe" }
    if (Test-Path $ollama) { Start-Process -FilePath $ollama -ArgumentList "serve" -WindowStyle Hidden }
    else { Write-Host "Ollama não encontrado: rode 'Instalar dependências da Nora' no menu Iniciar." -ForegroundColor Yellow }
}

if (-not (Responde $PortaWhisper)) {
    $servidor = Get-ChildItem -Path (Join-Path $pasta "ferramentas\whisper") -Recurse -Filter "whisper-server.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
    # The most accurate model that is downloaded.
    $modelo = foreach ($nome in "large-v3-turbo-q5_0", "large-v3-turbo", "medium", "small", "base") {
        $arquivo = Join-Path $pasta "models\ggml-$nome.bin"
        if (Test-Path $arquivo) { $arquivo; break }
    }
    if ($servidor -and $modelo) {
        $threads = [Math]::Max(1, [Environment]::ProcessorCount - 2)
        Start-Process -FilePath $servidor.FullName -WorkingDirectory $servidor.DirectoryName -WindowStyle Minimized -ArgumentList @(
            "-m", "`"$modelo`"", "-l", "pt", "-t", $threads, "--host", "127.0.0.1", "--port", $PortaWhisper)
    } else {
        Write-Host "Ouvido (whisper.cpp) não encontrado: rode 'Instalar dependências da Nora' no menu Iniciar." -ForegroundColor Yellow
    }
}

# The HUD opens in the browser as soon as its server is up.
Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoProfile", "-Command", "Start-Sleep -Seconds 5; Start-Process 'http://127.0.0.1:$PortaHud/'"
& (Join-Path $programa "nora.exe") ouvir --hud --hud-porta $PortaHud
if ($LASTEXITCODE) { Read-Host "A Nora fechou com erro ($LASTEXITCODE). Aperte Enter para fechar" | Out-Null }
