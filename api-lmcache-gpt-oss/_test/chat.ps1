param(
    [string]$Uri = "http://localhost:8000/v1/chat/completions",
    [string]$Model = "openai/gpt-oss-20b",
    [string]$Question = "Escribe una lista de 5 ideas para cena rápida",
    [int]$MaxTokens = 128,
    [double]$Temperature = 0.7
)

$payload = @{
  model = $Model
  messages = @(@{ role = "user"; content = $Question })
  max_tokens = $MaxTokens
  temperature = $Temperature
} | ConvertTo-Json -Depth 5

try {
  $resp = Invoke-RestMethod -Method POST -Uri $Uri -ContentType "application/json" -Body $payload -TimeoutSec 300
  if ($null -ne $resp -and $resp.choices.Count -gt 0) {
    Write-Host "===> Respuesta del modelo:" -ForegroundColor Cyan
    $resp.choices[0].message.content
  } else {
    Write-Warning ("Respuesta inesperada del servidor:`n{0}" -f ($resp | ConvertTo-Json -Depth 10))
  }
} catch {
  Write-Error ("Error llamando a ${Uri}: {0}" -f $_.Exception.Message)
  exit 1
}