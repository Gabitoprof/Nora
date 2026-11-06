# Homologação v0.4.0 no Windows: roda sozinho tudo o que não precisa de você e grava os números.
# Uso, na pasta do repositório, com o ambiente ativado (.venv\Scripts\activate):
#   powershell -ExecutionPolicy Bypass -File scripts\homologacao_windows.ps1
# Sem a medição de desempenho (só testes): acrescente -SemDesempenho
# O resultado vai para data\homologacao\AAAA-MM-DD_HHMM.txt (fora do Git). Mande esse arquivo.

param(
    [switch]$SemDesempenho,
    [int]$Segundos = 30,
    [int]$PortaHud = 8765
)

$ErrorActionPreference = "Continue"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz
if (-not $env:VIRTUAL_ENV) { throw "Ative o ambiente antes: .venv\Scripts\activate" }
$pasta = Join-Path $raiz "data\homologacao"
New-Item -ItemType Directory -Force -Path $pasta | Out-Null
$arquivo = Join-Path $pasta ((Get-Date -Format "yyyy-MM-dd_HHmm") + ".txt")
function Anotar([string]$texto) { $texto | Tee-Object -FilePath $arquivo -Append }
function Etapa([string]$nome, [scriptblock]$bloco) {
    Anotar "`n== $nome =="
    $inicio = Get-Date
    try { & $bloco 2>&1 | ForEach-Object { "$_" } | Select-Object -Last 15 | ForEach-Object { Anotar "  $_" } }
    catch { Anotar "  ERRO: $($_.Exception.Message)" }
    Anotar ("  ({0:N0} s)" -f ((Get-Date) - $inicio).TotalSeconds)
}

Anotar "Homologação Nora - $(Get-Date -Format 'dd/MM/yyyy HH:mm')"
Anotar "Branch: $(git branch --show-current)  Commit: $(git rev-parse --short HEAD)"
Anotar "Python: $(python --version 2>&1)  Node: $(node --version 2>&1)"
Anotar "Nora: $(python -c 'import nora; print(nora.__version__, nora.commit())' 2>&1)"
Get-CimInstance Win32_VideoController | ForEach-Object { Anotar "GPU: $($_.Name) (driver $($_.DriverVersion))" }
Anotar "CPU: $((Get-CimInstance Win32_Processor | Select-Object -First 1).Name)"

Etapa "pytest" { python -m pytest -q -p no:cacheprovider }
Etapa "ruff" { ruff format --check .; ruff check . }
Etapa "instalação limpa (wheel fora do checkout)" { python scripts\testar_instalacao_limpa.py }
Push-Location (Join-Path $raiz "hud")
Etapa "HUD: npm ci" { npm ci --no-audit --no-fund }
Etapa "HUD: npm test" { npm test }
Etapa "HUD: npm run build" { npm run build }
Pop-Location
Etapa "nora --verificar" { nora --verificar }

if (-not $SemDesempenho) {
    Anotar "`n== Desempenho: HUD aberta e modelo local carregado, $Segundos s =="
    $modelo = python -c "from nora.config import carregar; print(carregar().modelo_local.modelo)" 2>$null
    try {
        # Carrega o modelo na GPU sem gerar texto (mesmo pedido que a Nora faz ao aquecer).
        Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:11434/api/generate" -ContentType "application/json" `
            -Body (@{ model = $modelo; keep_alive = "10m" } | ConvertTo-Json) -TimeoutSec 120 | Out-Null
        Anotar "  modelo carregado: $modelo"
    } catch { Anotar "  AVISO: não consegui carregar $modelo no Ollama ($($_.Exception.Message))" }
    (& ollama ps 2>&1) | ForEach-Object { Anotar "  ollama ps: $_" }
    $hud = Start-Process -FilePath python -ArgumentList "-m", "nora", "hud", "--porta", $PortaHud -PassThru -WindowStyle Minimized
    Start-Sleep -Seconds 3
    Start-Process "http://127.0.0.1:$PortaHud/"
    Anotar "  HUD aberta no navegador (deixe a janela visível, em tela cheia se puder)"
    Start-Sleep -Seconds 5
    $nucleos = [Environment]::ProcessorCount
    $amostras = @()
    for ($i = 0; $i -lt $Segundos; $i++) {
        $gpu3d = (Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -like "*engtype_3D*" } | Measure-Object UtilizationPercentage -Sum).Sum
        $vram = (Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUAdapterMemory -ErrorAction SilentlyContinue |
            Measure-Object DedicatedUsage -Sum).Sum / 1GB
        $procs = Get-CimInstance Win32_PerfFormattedData_PerfProc_Process -ErrorAction SilentlyContinue
        $cpuTotal = ($procs | Where-Object { $_.Name -eq "_Total" }).PercentProcessorTime / $nucleos
        $cpuNav = ($procs | Where-Object { $_.Name -match "^(msedge|chrome|firefox)" } | Measure-Object PercentProcessorTime -Sum).Sum / $nucleos
        $cpuPy = ($procs | Where-Object { $_.Name -match "^python" } | Measure-Object PercentProcessorTime -Sum).Sum / $nucleos
        $amostras += [pscustomobject]@{ gpu3d = $gpu3d; vram = $vram; cpu = $cpuTotal; navegador = $cpuNav; python = $cpuPy }
        Start-Sleep -Milliseconds 700
    }
    foreach ($campo in "gpu3d", "vram", "cpu", "navegador", "python") {
        $m = $amostras | Measure-Object $campo -Average -Maximum -Minimum
        $unidade = if ($campo -eq "vram") { "GB" } else { "%" }
        Anotar ("  {0,-10} média {1,6:N1}  mín {2,6:N1}  máx {3,6:N1} {4}" -f $campo, $m.Average, $m.Minimum, $m.Maximum, $unidade)
    }
    Anotar "  (gpu3d = soma dos motores 3D; vram = memória dedicada em uso; cpu em % do total da máquina)"
    Stop-Process -Id $hud.Id -ErrorAction SilentlyContinue
}

Anotar "`nPronto: $arquivo"
