# Teste de compatibilidade da GPU AMD com o Ollama (preparação da v0.1.0).
# Uso, no PowerShell, dentro da pasta do repositório:
#   powershell -ExecutionPolicy Bypass -File scripts\teste_gpu_windows.ps1
# O resultado também é salvo em data\teste-gpu-<data>.txt (fora do Git).

param(
    [string]$Modelo = "qwen3.5:9b",
    [switch]$PularDownload
)

$ErrorActionPreference = "Continue"
$raiz = Split-Path -Parent $PSScriptRoot
$pastaDados = Join-Path $raiz "data"
New-Item -ItemType Directory -Force -Path $pastaDados | Out-Null
$relatorio = Join-Path $pastaDados ("teste-gpu-" + (Get-Date -Format "yyyy-MM-dd_HH-mm") + ".txt")

function Escrever([string]$texto) {
    Write-Host $texto
    Add-Content -Path $relatorio -Value $texto -Encoding UTF8
}

Escrever "=== Teste de GPU - $(Get-Date) ==="

Escrever "`n[1/4] Placas de vídeo"
Get-CimInstance Win32_VideoController | ForEach-Object {
    Escrever ("  {0} (driver {1})" -f $_.Name, $_.DriverVersion)
}

Escrever "`n[2/4] Ollama"
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Escrever "  Ollama não encontrado. Instale em https://ollama.com/download e rode o script de novo."
    exit 1
}
Escrever ("  " + (& ollama --version 2>&1 | Out-String).Trim())

if (-not $PularDownload) {
    Escrever "`n[3/4] Baixando $Modelo (pode levar vários minutos na primeira vez)"
    & ollama pull $Modelo
    if ($LASTEXITCODE -ne 0) { Escrever "  Falha ao baixar $Modelo."; exit 1 }
} else {
    Escrever "`n[3/4] Download pulado"
}

Escrever "`n[4/4] Medindo o tempo de resposta (pela API do Ollama)"
$hostOllama = if ($env:OLLAMA_HOST) { $env:OLLAMA_HOST } else { "http://127.0.0.1:11434" }
if ($hostOllama -notmatch "^https?://") { $hostOllama = "http://$hostOllama" }

function Medir([string]$rotulo, [bool]$pensar) {
    $corpo = @{
        model      = $Modelo
        prompt     = "Responda em uma frase curta, em português: qual é a capital do Brasil?"
        stream     = $false
        think      = $pensar
        keep_alive = "10m"
    } | ConvertTo-Json
    try {
        $r = Invoke-RestMethod -Uri "$hostOllama/api/generate" -Method Post `
            -ContentType "application/json; charset=utf-8" `
            -Body ([System.Text.Encoding]::UTF8.GetBytes($corpo))
    } catch {
        Escrever "  ${rotulo}: falhou ($($_.Exception.Message))"
        return
    }
    $total = [math]::Round($r.total_duration / 1e9, 2)
    $carga = [math]::Round($r.load_duration / 1e9, 2)
    $tps = if ($r.eval_duration -gt 0) { [math]::Round($r.eval_count / ($r.eval_duration / 1e9), 1) } else { 0 }
    $pensou = if ($r.thinking) { $r.thinking.Length } else { 0 }
    Escrever ("  {0}" -f $rotulo)
    Escrever ("    resposta:        {0}" -f $r.response.Trim())
    Escrever ("    tempo total:     {0} s (carga do modelo: {1} s)" -f $total, $carga)
    Escrever ("    velocidade:      {0} tokens/s ({1} tokens gerados)" -f $tps, $r.eval_count)
    if ($pensar) { Escrever ("    raciocínio:      {0} caracteres antes de responder" -f $pensou) }
}

Medir "Aquecimento (carrega o modelo na GPU)" $false
Medir "Sem modo pensando (como será na conversa por voz)" $false
Medir "Com modo pensando (para comparar)" $true

Escrever "`n  Onde o modelo está rodando (coluna PROCESSOR):"
& ollama ps 2>&1 | ForEach-Object { Escrever "  $_" }

Escrever "`n=== Como ler ==="
Escrever "  PROCESSOR '100% GPU'  -> a placa AMD está sendo usada. Ótimo."
Escrever "  PROCESSOR com 'CPU'   -> a placa não foi usada. Veja docs/TESTE_GPU.md (seção 'Se rodar na CPU')."
Escrever "  velocidade            -> acima de ~30 tokens/s a conversa fica fluida."
Escrever "  tempo total           -> sem modo pensando, o ideal é ficar abaixo de ~1 s com o modelo já carregado."
Escrever "`nRelatório salvo em: $relatorio"
