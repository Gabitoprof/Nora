# Homologação v0.4.0 no Windows: roda sozinho tudo o que não precisa de você e grava os números.
# Uso, na pasta do repositório, com o ambiente ativado (.venv\Scripts\activate):
#   powershell -ExecutionPolicy Bypass -File scripts\homologacao_windows.ps1
# Sem a medição de desempenho (só testes): acrescente -SemDesempenho
# Só a medição (sem os testes): -SoMedir. Teste contínuo de 25 min no fim: -Continuo (-Minutos 30).
# O resultado vai para data\homologacao\AAAA-MM-DD_HHMM.txt (fora do Git). Mande esse arquivo.

param(
    [switch]$SemDesempenho,
    [switch]$SoMedir,
    [switch]$Continuo,
    [int]$Segundos = 60,
    [int]$Minutos = 25,
    [int]$Intervalo = 10
)

$ErrorActionPreference = "Continue"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz
if (-not $env:VIRTUAL_ENV) { throw "Ative o ambiente antes: .venv\Scripts\activate" }
$pasta = Join-Path $raiz "data\homologacao"
New-Item -ItemType Directory -Force -Path $pasta | Out-Null
$arquivo = Join-Path $pasta ((Get-Date -Format "yyyy-MM-dd_HHmm") + ".txt")
# UTF-8 nos dois PowerShell (o Tee-Object do 5.1 gravaria em UTF-16).
function Anotar([string]$texto) { Write-Host $texto; Add-Content -Path $arquivo -Value $texto -Encoding UTF8 }
$script:falhas = @()
function Etapa([string]$nome, [scriptblock]$bloco, [int]$Ultimas = 15) {
    Anotar "`n== $nome =="
    $inicio = Get-Date
    $global:LASTEXITCODE = 0
    try {
        # Avisos no stderr (npm, vite) chegam como ErrorRecord: mostra só o texto, sem linhas vazias.
        & $bloco 2>&1 | ForEach-Object {
            if ($_ -is [System.Management.Automation.ErrorRecord]) { $_.Exception.Message } else { "$_" }
        } | Where-Object { $_.Trim() -ne "" } | Select-Object -Last $Ultimas | ForEach-Object { Anotar "  $_" }
        $codigo = $global:LASTEXITCODE
    } catch { Anotar "  ERRO: $($_.Exception.Message)"; $codigo = -1 }
    $tempo = "{0:N0} s" -f ((Get-Date) - $inicio).TotalSeconds
    if ($codigo -ne 0) {
        $script:falhas += $nome
        Anotar "  FALHOU (código $codigo, $tempo)"
    } else { Anotar "  ok ($tempo)" }
}

Anotar "Homologação Nora - $(Get-Date -Format 'dd/MM/yyyy HH:mm')"
Anotar "Branch: $(git branch --show-current)  Commit: $(git rev-parse --short HEAD)"
Anotar "Python: $(python --version 2>&1)  Node: $(node --version 2>&1)"
Anotar "Nora: $(python -c 'import nora; print(nora.__version__, nora.commit())' 2>&1)"
Get-CimInstance Win32_VideoController | ForEach-Object { Anotar "GPU: $($_.Name) (driver $($_.DriverVersion))" }
Anotar "CPU: $((Get-CimInstance Win32_Processor | Select-Object -First 1).Name)"

if (-not $SoMedir) {
    Etapa "pytest" { python -m pytest -q -p no:cacheprovider }
    Etapa "ruff" { ruff format --check .; ruff check . }
    Etapa "instalação limpa (wheel fora do checkout)" { python (Join-Path (Join-Path $raiz "scripts") "testar_instalacao_limpa.py") }
    Push-Location (Join-Path $raiz "hud")
    Etapa "HUD: npm ci" { npm ci --no-audit --no-fund }
    Etapa "HUD: npm test" { npm test }
    Etapa "HUD: npm run build" { npm run build }
    Pop-Location
    Etapa "nora --verificar" { nora --verificar } -Ultimas 80
}

# --- Medição de desempenho (roadmap "Imagem para as falas", item 9) -------------------------------
# Tudo com a Nora real rodando (Qwen, Whisper e ElevenLabs ao mesmo tempo): `nora ouvir --hud`
# num terminal, o ouvido aberto, e a HUD no navegador. As classes CIM abaixo têm o mesmo nome em
# qualquer idioma do Windows (os contadores do Get-Counter mudam de nome em português).
$nucleos = [Environment]::ProcessorCount
$dados = python -c "from nora.config import carregar; print(carregar().pasta_dados)" 2>$null
if (-not $dados) { $dados = Join-Path $raiz "data" }
$arquivoHud = Join-Path $dados "diagnostico_hud.json"
$navegadores = "^(msedge|chrome|firefox|brave|opera)"

function Amostra {
    $procs = Get-CimInstance Win32_PerfFormattedData_PerfProc_Process -ErrorAction SilentlyContinue
    $nav = $procs | Where-Object { $_.Name -match $navegadores }
    $pidsNav = @($nav | ForEach-Object { [int]$_.IDProcess })
    $gpuProc = Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUProcessMemory -ErrorAction SilentlyContinue
    $vramNav = 0
    foreach ($g in $gpuProc) {
        if ($g.Name -match "^pid_(\d+)_" -and $pidsNav -contains [int]$Matches[1]) { $vramNav += [double]$g.DedicatedUsage }
    }
    $vramTotal = (Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUAdapterMemory -ErrorAction SilentlyContinue |
        Measure-Object DedicatedUsage -Sum).Sum
    $gpu3d = (Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "*engtype_3D*" } | Measure-Object UtilizationPercentage -Sum).Sum
    function Cpu($filtro) { (($procs | Where-Object { $_.Name -match $filtro }) | Measure-Object PercentProcessorTime -Sum).Sum / $nucleos }
    [pscustomobject]@{
        hora = Get-Date -Format "HH:mm:ss"
        cpu_total = ($procs | Where-Object { $_.Name -eq "_Total" }).PercentProcessorTime / $nucleos
        cpu_navegador = Cpu $navegadores
        cpu_nora = Cpu "^(python|nora)"
        cpu_ollama = Cpu "^ollama"
        cpu_whisper = Cpu "^whisper"
        gpu3d = [double]$gpu3d
        vram_total_mb = [double]$vramTotal / 1MB
        vram_navegador_mb = $vramNav / 1MB
        memoria_navegador_mb = (($nav | Measure-Object WorkingSetPrivate -Sum).Sum) / 1MB
    }
}
function Media($amostras, $campo) { ($amostras | Measure-Object $campo -Average).Average }
function LerHud {
    if (Test-Path $arquivoHud) { try { return Get-Content $arquivoHud -Raw -Encoding UTF8 | ConvertFrom-Json } catch {} }
    return $null
}
function Medir([int]$segundos) {
    $lista = @()
    $fim = (Get-Date).AddSeconds($segundos)
    while ((Get-Date) -lt $fim) { $lista += Amostra; Start-Sleep -Seconds 2 }
    return $lista
}
function Meta([string]$nome, [double]$valor, [double]$limite, [string]$unidade) {
    $ok = if ($valor -le $limite) { "ok" } else { "ACIMA DA META" }
    Anotar ("  {0,-34} {1,8:N1} {2,-3} (meta <= {3} {2}) {4}" -f $nome, $valor, $unidade, $limite, $ok)
}

if (-not $SemDesempenho) {
    Anotar "`n== Desempenho da HUD com a Nora real ($Segundos s por fase) =="
    Anotar "  Num outro terminal: nora ouvir --hud (com o ouvido aberto e o ElevenLabs configurado)."
    Read-Host "  1) Deixe a Nora rodando e FECHE a aba da HUD no navegador. Aperte Enter para medir a base" | Out-Null
    $base = Medir $Segundos
    Read-Host "  2) Abra a HUD (Ctrl+F5), deixe visível e converse com ela usando o roteiro. Aperte Enter para medir" | Out-Null
    $comHud = Medir $Segundos
    $hud = LerHud
    $cpuMais = (Media $comHud cpu_total) - (Media $base cpu_total)
    $vramMais = (Media $comHud vram_total_mb) - (Media $base vram_total_mb)
    Anotar ("  base:    CPU {0:N1}%  VRAM {1:N0} MB  GPU 3D {2:N0}%" -f (Media $base cpu_total), (Media $base vram_total_mb), (Media $base gpu3d))
    Anotar ("  com HUD: CPU {0:N1}%  VRAM {1:N0} MB  GPU 3D {2:N0}%  (navegador: CPU {3:N1}%, VRAM {4:N0} MB)" -f `
        (Media $comHud cpu_total), (Media $comHud vram_total_mb), (Media $comHud gpu3d), (Media $comHud cpu_navegador), (Media $comHud vram_navegador_mb))
    Meta "CPU a mais com a HUD (pontos %)" $cpuMais 10 "pp"
    Meta "VRAM a mais com a HUD" $vramMais 256 "MB"
    if ($hud) {
        Anotar ("  HUD ({0} quadros em {1} s, limite {2} FPS): quadro p50 {3} ms, p95 {4} ms, pior {5} ms; trabalho p95 {6} ms" -f `
            $hud.quadros, $hud.janela_s, $hud.fps_limite, $hud.intervalo_p50, $hud.intervalo_p95, $hud.intervalo_pior, $hud.trabalho_p95)
        Meta "Tempo de quadro p95" $hud.intervalo_p95 33.3 "ms"
        if ($hud.palavras -gt 0) { Meta "Atraso som -> palavra p95 ($($hud.palavras) palavras)" $hud.atraso_palavra_p95 100 "ms" }
        else { Anotar "  Atraso som -> palavra: nenhuma palavra mostrada (ligue Visível e 'Palavras em partículas')" }
        Anotar "  Contextos WebGL: $($hud.contextos_webgl) criado(s), $($hud.contextos_perdidos) perdido(s)"
    } else { Anotar "  AVISO: a HUD não gravou $arquivoHud (ela grava a cada 10 s quando conectada)." }
}

if ($Continuo) {
    $csv = Join-Path $pasta ((Get-Date -Format "yyyy-MM-dd_HHmm") + "_continuo.csv")
    Anotar "`n== Teste contínuo: $Minutos min, uma amostra a cada $Intervalo s =="
    Anotar "  Deixe a HUD aberta e a Nora em uso (converse de vez em quando). Planilha: $csv"
    $linhas = @()
    $fim = (Get-Date).AddMinutes($Minutos)
    while ((Get-Date) -lt $fim) {
        $a = Amostra
        $h = LerHud
        $a | Add-Member quadro_p95_ms $(if ($h) { $h.intervalo_p95 } else { $null })
        $a | Add-Member contextos_webgl $(if ($h) { $h.contextos_webgl } else { $null })
        $a | Add-Member memoria_js_mb $(if ($h) { $h.memoria_js_mb } else { $null })
        $linhas += $a
        $a | Export-Csv -Path $csv -Append -NoTypeInformation -Encoding UTF8
        $restante = [int]($fim - (Get-Date)).TotalMinutes
        Write-Host ("  {0}  CPU {1:N1}%  VRAM {2:N0} MB  navegador {3:N0} MB  quadro p95 {4} ms  ({5} min restantes)" -f `
            $a.hora, $a.cpu_total, $a.vram_total_mb, $a.memoria_navegador_mb, $a.quadro_p95_ms, $restante)
        Start-Sleep -Seconds $Intervalo
    }
    $n = [Math]::Max(1, [int](120 / $Intervalo))  # primeiros e últimos ~2 min
    $comeco = $linhas | Select-Object -First $n
    $final = $linhas | Select-Object -Last $n
    foreach ($campo in "cpu_total", "vram_total_mb", "memoria_navegador_mb", "memoria_js_mb", "quadro_p95_ms", "contextos_webgl") {
        $a = Media $comeco $campo; $b = Media $final $campo
        Anotar ("  {0,-22} início {1,8:N1}  fim {2,8:N1}  diferença {3,8:N1}" -f $campo, $a, $b, ($b - $a))
    }
    Anotar "  Sinais de problema: memória ou VRAM subindo sem parar, contextos WebGL aumentando, quadro p95 piorando."
}

if ($script:falhas.Count) { Anotar "`nATENÇÃO: falharam $($script:falhas.Count) etapa(s): $($script:falhas -join ', ')" }
else { Anotar "`nTodas as etapas passaram." }
Anotar "Pronto: $arquivo"
