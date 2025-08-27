# test-vram-conc.ps1 - Escenario único (VRAM/Concurrency) para OCR MinerU

# Directorio base del script
$scriptRoot = $PSScriptRoot

# --- Configuración mínima (ajusta si necesitas) ---
$baseUrl    = "http://localhost:8001"
$inputFile  = Join-Path $scriptRoot "test-factura.pdf"
$outputDir  = Join-Path $scriptRoot "result"
$vram       = 16000  # en MB (p. ej., 2048, 4096, 8192)
$concurrency= 10     # número de workers concurrentes
$perWorker  = 896    # MB por worker (opcional). Ajusta a 1024 si priorizas estabilidad
# -----------------------------------------------

# Verificar que el archivo de entrada exista
if (-not (Test-Path $inputFile)) {
    Write-Error "El archivo de entrada no se encuentra en: $inputFile"
    exit 1
}

# Crear el directorio de salida si no existe
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir | Out-Null
}

# Preparar nombres
$vramGB   = [int]([Math]::Round($vram / 1024.0))
$label    = "${vramGB}GB/${concurrency}x"
$prefix   = "ocr_${vramGB}GB_${concurrency}x"
$stamp    = Get-Date -Format "yyyyMMdd_HHmmss"
$outputFile = Join-Path $outputDir ("{0}_{1}.zip" -f $prefix, $stamp)

# Medir tiempo
$sw = [System.Diagnostics.Stopwatch]::StartNew()

Write-Host "Ejecutando escenario '$label'..."

# Llamada al endpoint OCR (form-data)
curl.exe -sS -X POST "$baseUrl/ocr" `
    -F ("file=@" + $inputFile) `
    -F ("vram_limit=" + $vram) `
    -F ("concurrency=" + $concurrency) `
    -F ("per_worker_mb=" + $perWorker) `
    --output $outputFile | Out-Null

$sw.Stop()

# Resultado
Write-Host "`n--- Resultado ---"
[PSCustomObject]@{
    Escenario = $label
    Tiempo_s  = [Math]::Round($sw.Elapsed.TotalSeconds, 2)
    Salida    = $outputFile
} | Format-Table -AutoSize
