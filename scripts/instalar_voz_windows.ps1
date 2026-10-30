# Instala o ouvido (whisper.cpp) e a voz (Piper) da Ella no Windows.
# Uso, no PowerShell, na pasta do repositório e COM O AMBIENTE ATIVADO (.venv\Scripts\activate):
#   powershell -ExecutionPolicy Bypass -File scripts\instalar_voz_windows.ps1
# Tudo vai para ferramentas\ e models\, que ficam fora do Git.

param(
    [string]$ModeloWhisper = "small",
    [string]$Voz = "pt_BR-faber-medium"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"  # a barra de progresso deixa downloads grandes muito lentos
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$raiz = Split-Path -Parent $PSScriptRoot
if (-not $env:VIRTUAL_ENV) {
    throw "Ative o ambiente antes: .venv\Scripts\activate (senão o Piper vai para o Python errado)."
}
$ferramentas = Join-Path $raiz "ferramentas"
$modelos = Join-Path $raiz "models"
New-Item -ItemType Directory -Force -Path $ferramentas, $modelos | Out-Null

Write-Host "`n[1/4] whisper.cpp (versão oficial para processador)"
$pastaWhisper = Join-Path $ferramentas "whisper"
$servidor = Get-ChildItem -Path $pastaWhisper -Recurse -Filter "whisper-server.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($servidor) {
    Write-Host "  já instalado: $($servidor.FullName)"
} else {
    # Procura, entre as versões recentes, a mais nova que publicou o zip para Windows.
    $versoes = Invoke-RestMethod "https://api.github.com/repos/ggml-org/whisper.cpp/releases?per_page=15" `
        -Headers @{ "User-Agent" = "ella-instalador" }
    $escolha = $null
    foreach ($versao in $versoes) {
        if ($versao.prerelease -or $versao.draft) { continue }
        $arquivo = $versao.assets | Where-Object { $_.name -eq "whisper-bin-x64.zip" } | Select-Object -First 1
        if ($arquivo) { $escolha = $arquivo; Write-Host "  versão $($versao.tag_name)"; break }
    }
    if (-not $escolha) {
        Write-Host "  Arquivos da versão mais recente ($($versoes[0].tag_name)):"
        $versoes[0].assets | ForEach-Object { Write-Host "    $($_.name)" }
        throw "Não achei o whisper-bin-x64.zip nas versões recentes. Mande esta lista para o Claude."
    }
    $zip = Join-Path $ferramentas "whisper-bin-x64.zip"
    Invoke-WebRequest $escolha.browser_download_url -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath $pastaWhisper -Force
    Remove-Item $zip
    $servidor = Get-ChildItem -Path $pastaWhisper -Recurse -Filter "whisper-server.exe" | Select-Object -First 1
    if (-not $servidor) { throw "Não achei o whisper-server.exe dentro do zip baixado." }
    Write-Host "  instalado: $($servidor.FullName)"
}

Write-Host "`n[2/4] Modelo do Whisper ($ModeloWhisper, multilíngue; ~470 MB no small, pode demorar)"
$arquivoModelo = Join-Path $modelos "ggml-$ModeloWhisper.bin"
if (Test-Path $arquivoModelo) {
    Write-Host "  já baixado: $arquivoModelo"
} else {
    Invoke-WebRequest "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-$ModeloWhisper.bin" -OutFile $arquivoModelo
    Write-Host "  baixado: $arquivoModelo"
}

Write-Host "`n[3/4] Piper (licença GPL-3.0, roda como programa separado)"
python -m pip install --upgrade "piper-tts[http]"
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar o piper-tts." }

Write-Host "`n[4/4] Voz $Voz"
$pastaVozes = Join-Path $modelos "piper"
New-Item -ItemType Directory -Force -Path $pastaVozes | Out-Null
python -m piper.download_voices $Voz --data-dir $pastaVozes
if ($LASTEXITCODE -ne 0) { throw "Falha ao baixar a voz $Voz." }

Write-Host "`nPronto. Agora rode: powershell -ExecutionPolicy Bypass -File scripts\iniciar_voz_windows.ps1"
