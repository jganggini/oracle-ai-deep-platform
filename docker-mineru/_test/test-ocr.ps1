# test-ocr.ps1

$src = "C:\example\E54311224013702R001395301400.PDF"

$scenarios = @(
    @{ label = "2GB/10x"; vram = 2048; conc = 10; pref = "ocr_curl_2GB_10x" },
    @{ label = "4GB/5x";  vram = 4096; conc = 5;  pref = "ocr_curl_4GB_5x" },
    @{ label = "8GB/2x";  vram = 8192; conc = 2;  pref = "ocr_curl_8GB_2x" }
)

$results = @()

foreach ($s in $scenarios) {
    for ($i = 1; $i -le 3; $i++) {
        $out = ("D:\Downloads\{0}_{1}.zip" -f $s.pref, $i)
        $sw = [System.Diagnostics.Stopwatch]::StartNew()

        curl.exe -sS -X POST "http://localhost:8001/ocr" `
            -F ("file=@" + $src) `
            -F ("vram_limit=" + $s.vram) `
            -F ("concurrency=" + $s.conc) `
            -F "use_gpu=true" `
            -F "device=cuda" `
            -F "backend=pipeline" `
            --output $out | Out-Null

        $sw.Stop()

        $results += [PSCustomObject]@{
            Run      = $i
            VRAM     = $s.vram
            Conc     = $s.conc
            Pref     = $s.pref
            FileName = $out
            Time     = [Math]::Round($sw.Elapsed.TotalSeconds, 2)
        }
    }
}

$results | Format-Table Run, VRAM, Conc, Pref, FileName, Time -AutoSize