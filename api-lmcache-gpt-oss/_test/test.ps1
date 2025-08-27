$uri  = "http://localhost:8000/v1/chat/completions"
$body = @'
{
  "model": "openai/gpt-oss-20b",
  "messages": [{"role":"user","content":"Escribe una lista de 5 ideas para cena rápida"}],
  "max_tokens": 128
}
'@

# Guardar como UTF-8 sin BOM
$req = "$PWD\req.json"
[System.IO.File]::WriteAllText($req, $body, [System.Text.Encoding]::UTF8)

# Warm-up
1..3 | % {
  curl.exe -s -o NUL -w "warm %{http_code},%{time_total}`n" -X POST $uri -H "Content-Type: application/json" --data-binary "@$req" | Out-Null
}

# 8 en paralelo
$jobs = 1..8 | % {
  Start-Job { param($u,$f)
    curl.exe -s -o NUL -w "%{http_code},%{time_total}`n" -X POST $u -H "Content-Type: application/json" --data-binary "@$f"
  } -ArgumentList $uri,$req
}
$lines = $jobs | Receive-Job -Wait
$results = $lines | % { $p = $_ -split ","; [pscustomobject]@{ http=$p[0]; seconds=[double]$p[1] } }
$results | Format-Table

# stats
$p50 = ($results.seconds | Sort-Object)[[int]([math]::Floor($results.Count*0.5))-1]
$p95 = ($results.seconds | Sort-Object)[[int]([math]::Ceiling($results.Count*0.95))-1]
[pscustomobject]@{
  requests = $results.Count
  http_ok  = ($results | ? {$_.http -eq "200"}).Count
  p50_s    = "{0:N3}" -f $p50
  p95_s    = "{0:N3}" -f $p95
  max_s    = "{0:N3}" -f ($results.seconds | Measure-Object -Maximum | % Maximum)
  min_s    = "{0:N3}" -f ($results.seconds | Measure-Object -Minimum | % Minimum)
}