# Test mínimo PowerShell para LiteLLM Gateway

$base = "http://localhost:4000/litellm/oci/v1"
# Debe coincidir con API_KEY en .env del gateway
$apiKey = "oci-0KBMBRvyShvvylKXQX4S6wkplfVarQvRRuFUB3i9h9sdBYCviyVePg6YcR5GukOy6xwe3yDo8wSJlF7WCbbEt7qp4vvRdXnLidHGGdu0pkHPWuhWcMPqo0EATGiyZ3fn"

$headers = @{ Authorization = "Bearer $apiKey" }
$body = @{
  model = "xai.grok-4"
  messages = @(@{ role = "user"; content = "Hola, respóndeme en español." })
  temperature = 0
} | ConvertTo-Json -Depth 4

$response = Invoke-RestMethod -Method Post -Uri "$base/chat/completions" -Headers $headers -ContentType "application/json; charset=utf-8" -Body $body
[string]$response.choices[0].message.content
