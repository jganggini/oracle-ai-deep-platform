# test-performance.ps1 — Benchmark simplificado

$baseUrl   = "http://localhost:8001"
$scriptRoot = $PSScriptRoot
$inputFile = Join-Path $scriptRoot "test-factura.pdf"
$outputDir = Join-Path $scriptRoot "result"
$runs      = 3

if (-not (Test-Path $inputFile)) { Write-Error "No existe: $inputFile"; exit 1 }
if (-not (Test-Path $outputDir)) { New-Item -ItemType Directory -Path $outputDir | Out-Null }

$scenarios = @(
	@{ label = "per_worker=512 cap=6";  per_worker = 512;  cap = 6;  pref = "ocr_512mb_cap6" },
	@{ label = "per_worker=768 cap=6";  per_worker = 768;  cap = 6;  pref = "ocr_768mb_cap6" },
	@{ label = "per_worker=1024 cap=6"; per_worker = 1024; cap = 6;  pref = "ocr_1024mb_cap6" }
)

function Test-IsZip($path) {
	try {
		$bytes = Get-Content -LiteralPath $path -Encoding Byte -TotalCount 2
		return ($bytes -and $bytes.Length -ge 2 -and $bytes[0] -eq 80 -and $bytes[1] -eq 75) # 'PK'
	} catch { return $false }
}

$results = @()

foreach ($s in $scenarios) {
	for ($i = 1; $i -le $runs; $i++) {
		$out = Join-Path $outputDir ("{0}_run{1}.zip" -f $s.pref, $i)
		Write-Host "Escenario '$($s.label)' Run #$i..."
		$sw = [System.Diagnostics.Stopwatch]::StartNew()

		curl.exe -sS -X POST "$baseUrl/ocr" `
			-F ("file=@" + $inputFile) `
			-F ("per_worker_mb=" + $s.per_worker) `
			-F ("workers_cap=" + $s.cap) `
			--output $out | Out-Null

		$sw.Stop()

		if (Test-IsZip $out) {
			$results += [PSCustomObject]@{
				Escenario    = $s.label
				Run          = $i
				PerWorker_MB = $s.per_worker
				Cap          = $s.cap
				Tiempo_s     = [Math]::Round($sw.Elapsed.TotalSeconds, 2)
				Salida       = $out
			}
		} else {
			Write-Warning "Falló $($s.label) Run #$i (no ZIP)."
		}
	}
}

Write-Host "`n--- Resultados del Benchmark (detalle) ---"
$results | Format-Table Escenario, Run, PerWorker_MB, Cap, Tiempo_s, Salida -AutoSize

Write-Host "`n--- Promedio por escenario ---"
$summary = $results | Group-Object Escenario | ForEach-Object {
	[PSCustomObject]@{
		Escenario  = $_.Name
		Runs_ok    = $_.Count
		Promedio_s = [Math]::Round((($_.Group | Measure-Object Tiempo_s -Average).Average), 2)
	}
}
$summary | Sort-Object Promedio_s | Format-Table Escenario, Runs_ok, Promedio_s -AutoSize