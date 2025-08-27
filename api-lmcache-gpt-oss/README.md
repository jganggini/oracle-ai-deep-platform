LMCache + vLLM (GPT-OSS) en Docker
=================================

Contenedor único que reemplaza el `docker-compose.yaml` para exponer la API OpenAI de vLLM con soporte de LMCache (offload CPU/disco). Basado en la imagen `vllm/vllm-openai:v0.10.1.1`.

Referencias: guía oficial utilizada para los flags y configuración de LMCache: [LMCache soporta GPT-OSS (20B/120B)](https://blog.lmcache.ai/2025-08-05-gpt-oss-support/).

Requisitos
----------
- Docker 24+
- GPU NVIDIA con drivers y `nvidia-container-toolkit`

Build
-----
```bash
docker build -t lmcache-gptoss:0.10.1.1 ./docker-lmcache
```

Run (Linux/macOS)
-----------------
```bash
docker run --rm \
  --gpus all \
  -p 8000:8000 \
  -v $(pwd)/lmcache-data:/lmcache-data \
  lmcache-gptoss:0.10.1.1
```

Run (Windows PowerShell)
------------------------
```powershell
docker run --rm `
  --gpus all `
  -p 8000:8000 `
  -v ${PWD}\lmcache-data:/lmcache-data `
  lmcache-gptoss:0.10.1.1
```

Valores por defecto
-------------------
- Modelo: `openai/gpt-oss-20b`
- Puerto: `8000`
- Max model len: `32768`
- GPU mem util: `0.80`
- dtype: `float16`
- Config LMCache: `/app/backend_cpu.yaml`

Probar la API
-------------
```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai/gpt-oss-20b",
    "messages": [{"role":"user","content":"Hola, ¿cómo estás?"}],
    "temperature": 0.7
  }'
```

Notas
-----
- El arranque usa `--kv-transfer-config` con `LMCacheConnectorV1` y `kv_role=kv_both`, y desactiva `hybrid-kv-cache-manager`, alineado con la guía oficial.
- Si cambias `backend_cpu.yaml`, puedes montar uno propio con `-v /ruta/custom.yaml:/app/backend_cpu.yaml`.
- Para 120B, ajusta `max_local_cpu_size` y considera aumentar el volumen/espacio de disco.
# Stack de LMCache: GPT-OSS 20B

## Características

- Setup simple para instalar y ejecutar LMCache con el modelo GPT-OSS 20B usando Docker.

## 🚀 Instalación Rápida

### 1. Construir y ejecutar - Primera vez
```bash
cp env.example .env
docker compose up -d --build
```

## 🔧 Configuración

### Configurar variables de entorno
```bash
cp env.example .env
# Editar .env si es necesario (LMCACHE_PORT)
```

### Variables de Entorno (.env)
```ini
# Puerto LMCache API
LMCACHE_PORT=8000
```

## 🚀 Instalación Rápida

```bash
docker run --gpus all  -p 8000:8000 --ipc=host vllm/vllm-openai:v0.10.1.1 --model openai/gpt-oss-20b
```

### Construir y ejecutar - Primera vez
```bash
docker run -d --rm --name gpt-oss `
  -p 8000:8000 `
  --gpus all `
  -v ${PWD}\backend_cpu.yaml:/app/backend_cpu.yaml:ro `
  -e LMCACHE_CONFIG_FILE=/app/backend_cpu.yaml `
  -e LMCACHE_USE_EXPERIMENTAL=True `
  vllm/vllm-openai:latest `
  --model openai/gpt-oss-20b `
  --max-model-len 32768 `
  --disable-hybrid-kv-cache-manager `
  --kv-transfer-config '{\"kv_connector\":\"LMCacheConnectorV1\",\"kv_role\":\"kv_both\"}'

# para no borrar 
docker run -d --name docker-lmcache `
  --restart unless-stopped `
  -p 8000:8000 `
  --gpus all `
  -v ${PWD}\backend_cpu.yaml:/app/backend_cpu.yaml:ro `
  -v "D:\lmcache-data:/lmcache-data" `
  -e LMCACHE_CONFIG_FILE=/app/backend_cpu.yaml `
  -e LMCACHE_USE_EXPERIMENTAL=True `
  vllm/vllm-openai:latest `
  --model openai/gpt-oss-20b `
  --max-model-len 32768 `
  --disable-hybrid-kv-cache-manager `
  --kv-transfer-config '{\"kv_connector\":\"LMCacheConnectorV1\",\"kv_role\":\"kv_both\"}' `
  --chat-template-content-format openai `
  --uvicorn-log-level debug `
  --enable-log-requests `
  --disable-frontend-multiprocessing



```

docker compose up -d --build

# ver el log
docker logs -f docker-lmcache

# Eliminar 
docker rm -f docker-lmcache

### Prueba

curl http://localhost:8000/v1/models

```bash
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
```

### Siguientes veces
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Verificar funcionamiento
```bash
docker compose ps
```

### Probar endpoint
```bash
curl http://localhost:8000/
```

## 📁 Estructura del Proyecto

```
lmcache-gpt-oss/
├── main.py              # Aplicación FastAPI principal
├── requirements.txt     # Dependencias Python
├── Dockerfile.vllm-lmcache  # Dockerfile para LMCache
├── docker-compose.yaml  # Configuración Docker (usa .env)
├── env.example         # Variables de entorno de ejemplo
└── cache/              # Directorio para cache (se crea automáticamente)
```

## 📖 Uso

### Endpoints Disponibles
- `GET /` - Información del servicio
- `GET /health` - Estado de salud
- `POST /chat` - Chat con GPT-OSS (placeholder)

### Ejemplo de Chat

#### PowerShell (Windows)
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/chat" -Method POST -Headers @{"Content-Type"="application/json"} -Body '{"messages":[{"role": "user", "content":"Hola"}]}'
```

#### Bash/Linux/macOS
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role":"user", "content":"Hola, ¿cómo estás?"}
    ]
  }'
```

#### Respuesta esperada
```json
{
  "response": "Respuesta simulada para 1 mensajes usando openai/gpt-oss-20b",
  "cached": false
}
```

## 🐳 Comandos Docker Útiles

```bash
# Ver logs
docker compose logs -f

# Reiniciar servicio
docker compose restart

# Parar servicio
docker compose down

# Reconstruir después de cambios
docker compose up -d --build

# Verificar logs
docker compose logs lmcache

# Verificar estado del contenedor
docker compose ps
docker exec -it lmcache bash
```

## 📝 Notas

- Este es un setup básico para LMCache con GPT-OSS
- La integración completa con LMCache se implementará en futuras versiones
- El modelo GPT-OSS se descargará automáticamente cuando se configure la integración completa


