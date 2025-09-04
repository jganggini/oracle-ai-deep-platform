# test.ps1 — Ejemplo mínimo de uso del endpoint /ocr

$baseUrl = "http://localhost:8001"
$inFile  = Join-Path $PSScriptRoot "docs/test-factura.pdf"
$out     = Join-Path $PSScriptRoot "result.zip"
$extract = Join-Path $PSScriptRoot "result"

if (-not (Test-Path $inFile)) { Write-Error "No existe: $inFile"; exit 1 }
if (-not (Get-Command curl.exe -ErrorAction SilentlyContinue)) { Write-Error "curl.exe no encontrado"; exit 1 }
if (Test-Path $extract) { Remove-Item -Recurse -Force $extract }

$sw = [System.Diagnostics.Stopwatch]::StartNew()

curl.exe -sSf -X POST "$baseUrl/ocr" `
  -F ("file=@" + $inFile) `
  --output $out | Out-Null

$sw.Stop()
Write-Host ("Listo: {0} (Tiempo_s={1})" -f $out, [Math]::Round($sw.Elapsed.TotalSeconds,2))

# Extraer y validar estructura del ZIP
try {
  Expand-Archive -LiteralPath $out -DestinationPath $extract -Force
} catch {
  Write-Error "No se pudo extraer el ZIP de salida: $($_.Exception.Message)"; exit 1
}

$mdPath = Join-Path $extract "upload.md"
if (-not (Test-Path $mdPath)) { Write-Error "Falta upload.md en el ZIP"; exit 1 }

$jsonPath = Join-Path $extract "content_list.json"
$jsonOk = $false
if (Test-Path $jsonPath) {
  try {
    $json = Get-Content -LiteralPath $jsonPath -Raw | ConvertFrom-Json
    # No fallar si no es lista; solo verificar que sea JSON válido
    $jsonOk = $true
  } catch { $jsonOk = $false }
}

$mdContent = Get-Content -LiteralPath $mdPath -Raw
$imgMatches = [System.Text.RegularExpressions.Regex]::Matches($mdContent, '!\[[^\]]*\]\(([^)]+)\)')
$imagesOk = $true
foreach ($m in $imgMatches) {
  $rel = $m.Groups[1].Value
  if ($rel -like 'images/*') {
    $localPath = Join-Path $extract $rel
    if (-not (Test-Path $localPath)) { $imagesOk = $false; break }
  }
}

Write-Host "- upload.md: OK"
Write-Host ("- content_list.json: {0}" -f ($(if ($jsonOk) { 'OK' } elseif (Test-Path $jsonPath) { 'INVL' } else { 'NO' })))
Write-Host ("- Images: {0}" -f ($(if ($imagesOk) { 'OK' } else { 'FALTAN' })))

if (-not $imagesOk) { exit 2 }
exit 0
