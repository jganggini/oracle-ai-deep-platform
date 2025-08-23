# Stack de LMCache: GPT-OSS 20B

## Características

- Setup simple para instalar y ejecutar LMCache con el modelo GPT-OSS 20B usando Docker.

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

### Construir y ejecutar - Primera vez
```bash
docker compose up -d --build
```

### Siguientes veces
```bash
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


