# test.ps1 — Ejemplo mínimo de uso del endpoint /ocr

$baseUrl = "http://localhost:8001"
$inFile  = Join-Path $PSScriptRoot "test-factura.pdf"
$out     = Join-Path $PSScriptRoot "result.zip"

if (-not (Test-Path $inFile)) { Write-Error "No existe: $inFile"; exit 1 }
if (-not (Get-Command curl.exe -ErrorAction SilentlyContinue)) { Write-Error "curl.exe no encontrado"; exit 1 }

$sw = [System.Diagnostics.Stopwatch]::StartNew()

curl.exe -sSf -X POST "$baseUrl/ocr" `
  -F ("file=@" + $inFile) `
  -F ("per_worker_mb=1536") `
  -F ("workers_cap=6") `
  --output $out | Out-Null

$sw.Stop()
Write-Host ("Listo: {0} (Tiempo_s={1})" -f $out, [Math]::Round($sw.Elapsed.TotalSeconds,2))
