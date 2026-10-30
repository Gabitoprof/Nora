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

Escrever "`n[4/4] Gerando uma resposta e medindo a velocidade"
$saida = & ollama run $Modelo "Responda em uma frase curta, em português: qual é a capital do Brasil?" --verbose 2>&1 |
    ForEach-Object { "$_" }
$resposta = ($saida | Where-Object { $_ -notmatch "^(total duration|load duration|prompt eval|eval )" }) -join " "
Escrever ("  Resposta: " + $resposta.Trim())
$saida | Where-Object { $_ -match "^(load duration|prompt eval rate|eval rate)" } | ForEach-Object { Escrever "  $_" }

Escrever "`n  Onde o modelo está rodando (coluna PROCESSOR):"
& ollama ps 2>&1 | ForEach-Object { Escrever "  $_" }

Escrever "`n=== Como ler ==="
Escrever "  PROCESSOR '100% GPU'  -> a placa AMD está sendo usada. Ótimo."
Escrever "  PROCESSOR com 'CPU'   -> a placa não foi usada. Veja docs/TESTE_GPU.md (seção 'Se rodar na CPU')."
Escrever "  eval rate             -> tokens por segundo na resposta. Acima de ~30 tokens/s a conversa fica fluida."
Escrever "`nRelatório salvo em: $relatorio"
