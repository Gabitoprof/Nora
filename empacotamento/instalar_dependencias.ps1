# Nora's dependency pack: installs on its own what nora.exe uses and does not include.
#   - Visual C++ Redistributable (x64), if missing
#   - Ollama (local brain) and the models (qwen3.5:9b and bge-m3, ~7 GB)
#   - whisper.cpp (ear) and the Whisper model (~470 MB for small)
# All through winget (built into Windows 10/11) and the official sites. It goes to Nora's folder
# (%APPDATA%\Nora, or NORA_HOME). It can run again: what is already installed is skipped.
# Usage (Nora's installer offers to run it at the end; or from Start menu > Nora):
#   powershell -ExecutionPolicy Bypass -File instalar_dependencias.ps1
# Options: -ModeloWhisper large-v3-turbo-q5_0  -ModeloLocal qwen3.5:9b  -SemModelosOllama

param(
    [string]$ModeloWhisper = "small",
    [string]$ModeloLocal = "qwen3.5:9b",
    [string]$ModeloEmbeddings = "bge-m3",
    [switch]$SemModelosOllama
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"  # a barra de progresso deixa downloads grandes muito lentos
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$pasta = if ($env:NORA_HOME) { $env:NORA_HOME } else { Join-Path $env:APPDATA "Nora" }
$ferramentas = Join-Path $pasta "ferramentas"
$modelos = Join-Path $pasta "models"
$registros = Join-Path $pasta "instalacao"
New-Item -ItemType Directory -Force -Path $ferramentas, $modelos, $registros | Out-Null
Start-Transcript -Path (Join-Path $registros ("dependencias_" + (Get-Date -Format "yyyy-MM-dd_HHmm") + ".txt")) | Out-Null

$script:resultado = @()
function Etapa([string]$nome, [scriptblock]$bloco) {
    Write-Host "`n== $nome =="
    try { & $bloco; $script:resultado += "ok      $nome" }
    catch { Write-Host "  ERRO: $($_.Exception.Message)" -ForegroundColor Red; $script:resultado += "FALHOU  $nome" }
}
function Winget([string]$id) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "O winget não está neste Windows. Instale o 'Instalador de Aplicativo' (App Installer) pela Microsoft Store e rode de novo."
    }
    winget install --id $id --exact --silent --accept-package-agreements --accept-source-agreements
    # -1978335189: already installed, no update
    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne -1978335189) { throw "winget install $id terminou com código $LASTEXITCODE" }
}
function Ollama() {
    $comando = Get-Command ollama -ErrorAction SilentlyContinue
    if ($comando) { return $comando.Source }
    $padrao = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
    if (Test-Path $padrao) { return $padrao }
    return $null
}
function Responde([int]$porta) {
    $cliente = New-Object Net.Sockets.TcpClient
    try { $cliente.Connect("127.0.0.1", $porta); return $true } catch { return $false } finally { $cliente.Close() }
}

Write-Host "Pacote de dependências da Nora -> $pasta"

Etapa "Visual C++ Redistributable (x64)" {
    $vc = Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" -ErrorAction SilentlyContinue
    if ($vc -and $vc.Installed -eq 1) { Write-Host "  já instalado ($($vc.Version))" }
    else { Winget "Microsoft.VCRedist.2015+.x64" }
}

Etapa "Ollama (cérebro local)" {
    if (Ollama) { Write-Host "  já instalado: $(Ollama)" } else { Winget "Ollama.Ollama" }
    if (-not (Ollama)) { throw "O Ollama foi instalado, mas o ollama.exe não apareceu. Reinicie o Windows e rode de novo." }
}

if (-not $SemModelosOllama) {
    Etapa "Modelos do Ollama ($ModeloLocal e $ModeloEmbeddings, ~7 GB)" {
        $ollama = Ollama
        if (-not $ollama) { throw "Sem o Ollama, não dá para baixar os modelos." }
        if (-not (Responde 11434)) {
            Start-Process -FilePath $ollama -ArgumentList "serve" -WindowStyle Hidden
            for ($i = 0; $i -lt 30 -and -not (Responde 11434); $i++) { Start-Sleep -Seconds 1 }
        }
        foreach ($modelo in @($ModeloLocal, $ModeloEmbeddings)) {
            Write-Host "  baixando $modelo (pode demorar)..."
            & $ollama pull $modelo
            if ($LASTEXITCODE -ne 0) { throw "ollama pull $modelo terminou com código $LASTEXITCODE" }
        }
    }
}

Etapa "whisper.cpp (ouvido)" {
    $pastaWhisper = Join-Path $ferramentas "whisper"
    $servidor = Get-ChildItem -Path $pastaWhisper -Recurse -Filter "whisper-server.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($servidor) { Write-Host "  já instalado: $($servidor.FullName)"; return }
    # The newest version that published the Windows (CPU) zip.
    $versoes = Invoke-RestMethod "https://api.github.com/repos/ggml-org/whisper.cpp/releases?per_page=15" -Headers @{ "User-Agent" = "nora-instalador" }
    $escolha = $null
    foreach ($versao in $versoes) {
        if ($versao.prerelease -or $versao.draft) { continue }
        $arquivo = $versao.assets | Where-Object { $_.name -eq "whisper-bin-x64.zip" } | Select-Object -First 1
        if ($arquivo) { $escolha = $arquivo; Write-Host "  versão $($versao.tag_name)"; break }
    }
    if (-not $escolha) { throw "Não achei o whisper-bin-x64.zip nas versões recentes do whisper.cpp." }
    $zip = Join-Path $ferramentas "whisper-bin-x64.zip"
    Invoke-WebRequest $escolha.browser_download_url -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath $pastaWhisper -Force
    Remove-Item $zip
    $servidor = Get-ChildItem -Path $pastaWhisper -Recurse -Filter "whisper-server.exe" | Select-Object -First 1
    if (-not $servidor) { throw "Não achei o whisper-server.exe dentro do zip baixado." }
    Write-Host "  instalado: $($servidor.FullName)"
}

Etapa "Modelo do Whisper ($ModeloWhisper)" {
    $arquivo = Join-Path $modelos "ggml-$ModeloWhisper.bin"
    if (Test-Path $arquivo) { Write-Host "  já baixado: $arquivo"; return }
    Write-Host "  baixando (pode demorar)..."
    $parcial = "$arquivo.parcial"
    Invoke-WebRequest "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-$ModeloWhisper.bin" -OutFile $parcial
    Move-Item $parcial $arquivo -Force  # only counts once fully downloaded
    Write-Host "  baixado: $arquivo"
}

Write-Host "`n== Resumo =="
$script:resultado | ForEach-Object { Write-Host "  $_" }
$falhas = @($script:resultado | Where-Object { $_ -like "FALHOU*" }).Count
if ($falhas) { Write-Host "`n$falhas etapa(s) falharam. Rode de novo depois de corrigir; o que já está pronto é pulado." -ForegroundColor Yellow }
else { Write-Host "`nTudo pronto. Abra a Nora pelo menu Iniciar > Nora." -ForegroundColor Green }
Stop-Transcript | Out-Null
if (-not $env:NORA_SEM_PAUSA) { Read-Host "Aperte Enter para fechar" | Out-Null }
