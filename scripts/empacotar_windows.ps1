# Gera o nora.exe (sem assinatura) e o instalador da Nora no Windows.
# Uso, na pasta do repositório, num ambiente LIMPO e ativado (só o necessário vai para o .exe):
#   py -3.13 -m venv .venv-empacotar
#   .venv-empacotar\Scripts\activate
#   powershell -ExecutionPolicy Bypass -File scripts\empacotar_windows.ps1
# Precisa do Node.js 22 (HUD) e, para o instalador, do Inno Setup 6 (https://jrsoftware.org).
# Sem o Inno Setup, gera só o .zip. Resultado em dist\: Nora-<versão>-instalador.exe e .zip.
# A CI faz o mesmo (.github/workflows/empacotar.yml) e publica os arquivos na execução.

param([switch]$SemInstalador)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz
if (-not $env:VIRTUAL_ENV) { throw "Ative um ambiente limpo antes (veja o começo deste arquivo)." }
function Rodar([string]$descricao, [scriptblock]$bloco) {
    Write-Host "`n== $descricao =="
    & $bloco
    if ($LASTEXITCODE) { throw "$descricao falhou (código $LASTEXITCODE)" }
}

Rodar "dependências do .exe (voz, memória, nuvem) e PyInstaller" {
    python -m pip install --upgrade pip
    python -m pip install ".[voz,memoria,nuvem,empacotar]"
}
Rodar "build da HUD" { Push-Location hud; npm ci --no-audit --no-fund; npm run build; Pop-Location }

$versao = (python -c "import nora; print(nora.__version__)").Trim()
$commit = (git rev-parse --short HEAD).Trim()
$versaoArquivo = $versao -replace "\.dev", "-dev."
$arquivoCommit = Join-Path $raiz "src\nora\_commit.txt"
Set-Content -Path $arquivoCommit -Value $commit -Encoding ASCII -NoNewline
Write-Host "Nora $versao, commit $commit"

try {
    # De novo, agora com o _commit.txt dentro do pacote instalado.
    Rodar "pacote da Nora com o commit" { python -m pip install --no-deps --force-reinstall . }
    $hud = Join-Path $raiz "hud\dist"
    Rodar "PyInstaller (pasta, não arquivo único: abre mais rápido)" {
        python -m PyInstaller --noconfirm --clean --onedir --console --name nora `
            --distpath dist --workpath build\pyinstaller --specpath build\pyinstaller `
            --collect-data nora --collect-submodules nora `
            --collect-all sqlite_vec --collect-all sounddevice --collect-all soundfile `
            --exclude-module kokoro_onnx --exclude-module phonemizer --exclude-module tkinter `
            --add-data "$hud;hud\dist" `
            empacotamento\nora_exe.py
    }
} finally {
    Remove-Item $arquivoCommit -ErrorAction SilentlyContinue
}

$programa = Join-Path $raiz "dist\nora"
Rodar "avisos de licença dos componentes" { python empacotamento\juntar_licencas.py $programa }
Copy-Item LICENSE (Join-Path $programa "LICENSE.txt")
foreach ($arquivo in "instalar_dependencias.ps1", "iniciar_nora.ps1") { Copy-Item (Join-Path "empacotamento" $arquivo) $programa }
Copy-Item docs\INSTALACAO.md $programa

Write-Host "`n== teste rápido do nora.exe =="
$exe = Join-Path $programa "nora.exe"
$casa = Join-Path $env:TEMP ("nora-teste-" + [guid]::NewGuid().ToString("N"))
$env:NORA_HOME = $casa
try {
    $saida = & $exe --verificar 2>&1 | Out-String
    if ($LASTEXITCODE) { throw "nora.exe --verificar falhou:`n$saida" }
    if ($saida -notmatch "Versão: $([regex]::Escape($versao)) \(commit $commit\)") { throw "versão/commit errados:`n$saida" }
    if (-not (Test-Path (Join-Path $casa "config\local.toml"))) { throw "a pasta do usuário não foi criada" }
    Write-Host "  --verificar ok: $versao ($commit), pasta do usuário criada"
    $hudProc = Start-Process -FilePath $exe -ArgumentList "hud", "--porta", "8799" -PassThru -WindowStyle Hidden
    try {
        $pagina = $null
        for ($i = 0; $i -lt 20 -and -not $pagina; $i++) {
            Start-Sleep -Seconds 1
            try { $pagina = Invoke-WebRequest "http://127.0.0.1:8799/" -UseBasicParsing -TimeoutSec 2 } catch { }
        }
        if (-not $pagina -or $pagina.StatusCode -ne 200 -or $pagina.Content -notmatch "<div id=`"app`"") { throw "a HUD não respondeu de dentro do .exe" }
        Write-Host "  HUD servida pelo nora.exe: ok"
    } finally { Stop-Process -Id $hudProc.Id -Force -ErrorAction SilentlyContinue }
} finally {
    Remove-Item Env:NORA_HOME
    Remove-Item $casa -Recurse -Force -ErrorAction SilentlyContinue
}

$zip = Join-Path $raiz "dist\Nora-$versaoArquivo-windows.zip"
Remove-Item $zip -ErrorAction SilentlyContinue
Compress-Archive -Path $programa -DestinationPath $zip
Write-Host "`nZip: $zip"

if (-not $SemInstalador) {
    $iscc = @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($iscc) {
        Rodar "instalador (Inno Setup)" { & $iscc "/DVersao=$versaoArquivo" "/DCommit=$commit" empacotamento\nora.iss }
        Write-Host "Instalador: $(Join-Path $raiz "dist\Nora-$versaoArquivo-instalador.exe")"
    } else {
        Write-Host "Inno Setup 6 não encontrado: só o .zip foi gerado." -ForegroundColor Yellow
    }
}
Write-Host "`nPronto (sem assinatura: o Windows vai avisar na primeira vez; veja docs\INSTALACAO.md)."
