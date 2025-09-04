# test-multi-documents.ps1 — Benchmark por múltiples archivos (sin escenarios)

$baseUrl    = "http://localhost:8001"
$scriptRoot = $PSScriptRoot
$inputDir   = Join-Path $scriptRoot "docs"
$outputDir  = Join-Path $scriptRoot "result"
$runs       = 1

$files = Get-ChildItem -LiteralPath $inputDir -File | Where-Object { $_.Extension -match '^\.(pdf|PDF)$' }
if (-not $files -or $files.Count -eq 0) { Write-Error "No se encontraron PDFs en: $inputDir"; exit 1 }
if (-not (Test-Path $outputDir)) { New-Item -ItemType Directory -Path $outputDir | Out-Null }

function Test-IsZip($path) {
	try {
		$bytes = Get-Content -LiteralPath $path -Encoding Byte -TotalCount 2
		return ($bytes -and $bytes.Length -ge 2 -and $bytes[0] -eq 80 -and $bytes[1] -eq 75) # 'PK'
	} catch { return $false }
}

$filenameRegex = [regex]'filename="?([^";]+)"?'
function Get-RemoteFilenameFromHeaders($headerPath) {
	try {
		$lines = Get-Content -LiteralPath $headerPath -ErrorAction Stop
		foreach ($line in $lines) {
			if ($line -imatch '^content-disposition:') {
				$m = $filenameRegex.Match($line)
				if ($m.Success) { return $m.Groups[1].Value }
			}
		}
	} catch {}
	return $null
}

$results = @()

$allSw = [System.Diagnostics.Stopwatch]::StartNew()
$total = $files.Count
$idx = 0
foreach ($f in $files) {
	$idx++
	for ($i = 1; $i -le $runs; $i++) {
		$pref = [System.IO.Path]::GetFileNameWithoutExtension($f.Name)
		$tmpOut = Join-Path $outputDir ("{0}.tmp.zip" -f $pref)
		$hdr    = Join-Path $outputDir ("hdr_{0}_{1}.txt" -f $pref, ([guid]::NewGuid().ToString('N')))
		Write-Host ("[{0}/{1}] Procesando '{2}'..." -f $idx, $total, $f.Name)
		$sw = [System.Diagnostics.Stopwatch]::StartNew()

		$curl = Get-Command curl.exe -ErrorAction SilentlyContinue
		if (-not $curl) { Write-Error "curl.exe no encontrado"; exit 1 }

		$null = Start-Process -FilePath $curl.Path -ArgumentList @(
			"-sS", "-X", "POST", "$baseUrl/ocr",
			"-F", ("file=@" + $f.FullName),
			"-D", $hdr,
			"--output", $tmpOut
		) -PassThru -NoNewWindow -Wait

		$sw.Stop()
		$elapsed = [Math]::Round($sw.Elapsed.TotalSeconds, 2)
		# Resolver nombre final desde headers o fallback y renombrar
		$remoteName = Get-RemoteFilenameFromHeaders -headerPath $hdr
		Remove-Item -ErrorAction SilentlyContinue $hdr
		$finalOut = if ($remoteName) { Join-Path $outputDir $remoteName } else { Join-Path $outputDir ("{0}.zip" -f $pref) }
		if ((Test-Path $tmpOut) -and ($tmpOut -ne $finalOut)) {
			if (Test-Path $finalOut) { Remove-Item -Force $finalOut }
			Rename-Item -LiteralPath $tmpOut -NewName (Split-Path -Leaf $finalOut)
		}
		elseif (-not (Test-Path $finalOut) -and (Test-Path $tmpOut)) {
			Rename-Item -LiteralPath $tmpOut -NewName (Split-Path -Leaf $finalOut)
		}

		if (Test-IsZip $finalOut) {
			$pages = 0
			if ($finalOut -match "_P(\d{4})\.zip$") { try { $pages = [int]$Matches[1] } catch { $pages = 0 } }
			Write-Host ("[OK][time={0}s][pag={1}][out={2}]" -f $elapsed, $pages, $finalOut)
			$results += [PSCustomObject]@{
				Archivo   = $f.Name
				Paginas   = $pages
				Tiempo_s  = $elapsed
				Salida    = $finalOut
			}
		} else {
			Write-Warning ("Fallo ({0}s) → {1}" -f $elapsed, $finalOut)
		}
	}
}

Write-Host "`n--- Resultados (detalle) ---"
$results | Format-Table Archivo, Tiempo_s, Salida -AutoSize

Write-Host "`n--- Promedio por archivo ---"
$summary = $results | Group-Object Archivo | ForEach-Object {
	[PSCustomObject]@{
		Archivo    = $_.Name
		Runs_ok    = $_.Count
		Promedio_s = [Math]::Round((($_.Group | Measure-Object Tiempo_s -Average).Average), 2)
	}
}
$summary | Sort-Object Promedio_s | Format-Table Archivo, Runs_ok, Promedio_s -AutoSize

$allSw.Stop()
$ts = $allSw.Elapsed
$hhmmss = ('{0:00}:{1:00}:{2:00}' -f $ts.Hours, $ts.Minutes, $ts.Seconds)
Write-Host ("`nTiempo total: {0}" -f $hhmmss)