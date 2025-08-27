# test-ocr.ps1

# Directorio base del script
$scriptRoot = $PSScriptRoot

# --- Configuración ---
$inputFile = Join-Path $scriptRoot "test-factura.pdf" # https://www.gob.mx/cms/uploads/attachment/file/764689/84_2Tri_2022_COMPROBACION.pdf
$outputDir = Join-Path $scriptRoot "result"
# -------------------

# Verificar que el archivo de entrada exista
if (-not (Test-Path $inputFile)) {
    Write-Error "El archivo de entrada no se encuentra en: $inputFile"
    exit 1
}

# Crear el directorio de salida si no existe
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir | Out-Null
}

$scenarios = @(
    @{ label = "2GB/10x"; vram = 2048; conc = 10; pref = "ocr_2GB_10x" },
    @{ label = "4GB/5x";  vram = 4096; conc = 5;  pref = "ocr_4GB_5x" },
    @{ label = "8GB/2x";  vram = 8192; conc = 2;  pref = "ocr_8GB_2x" }
)

$results = @()

foreach ($s in $scenarios) {
    for ($i = 1; $i -le 3; $i++) {
        $outputFile = Join-Path $outputDir ("{0}_run{1}.zip" -f $s.pref, $i)
        $sw = [System.Diagnostics.Stopwatch]::StartNew()

        Write-Host "Ejecutando escenario '$($s.label)' (Run #$i)..."

        curl.exe -sS -X POST "http://localhost:8001/ocr" `
            -F ("file=@" + $inputFile) `
            -F ("vram_limit=" + $s.vram) `
            -F ("concurrency=" + $s.conc) `
            --output $outputFile | Out-Null

        $sw.Stop()

        $results += [PSCustomObject]@{
            Escenario = $s.label
            Run       = $i
            Tiempo_s  = [Math]::Round($sw.Elapsed.TotalSeconds, 2)
            Salida    = $outputFile
        }
    }
}

Write-Host "`n--- Resultados del Benchmark ---"
$results | Format-Table Escenario, Run, Tiempo_s, Salida -AutoSize