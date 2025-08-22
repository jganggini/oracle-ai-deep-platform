# LMCache con GPT-OSS 20B

Setup simple para instalar y ejecutar LMCache con el modelo GPT-OSS 20B usando Docker.

## 🚀 Instalación Rápida

### 1. Configurar variables de entorno
```bash
cp env.example .env
# Editar .env si es necesario
```

### 2. Construir y ejecutar
```bash
# Construir imagen
docker compose build

# Ejecutar servicio
docker compose up -d
```

### 3. Verificar funcionamiento
```bash
# Verificar estado
docker compose ps

# Probar endpoint
curl http://localhost:8000/
```

## 📁 Estructura del Proyecto

```
lmcache-gpt-oss/
├── main.py              # Aplicación FastAPI principal
├── requirements.txt     # Dependencias Python
├── Dockerfile.vllm-lmcache  # Dockerfile para LMCache
├── docker-compose.yaml  # Configuración Docker
├── env.example         # Variables de entorno de ejemplo
└── cache/              # Directorio para cache (se crea automáticamente)
```

## 🔧 Configuración

### Variables de Entorno (.env)
```ini
MODEL_ID=openai/gpt-oss-20b
LMCACHE_PORT=8000
```

### Puertos
- **8000**: LMCache API

## 📖 Uso

### Endpoints Disponibles
- `GET /` - Información del servicio
- `GET /health` - Estado de salud
- `POST /chat` - Chat con GPT-OSS (placeholder)

### Ejemplo de Chat

#### PowerShell (Windows)
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/chat" -Method POST -Headers @{"Content-Type"="application/json"} -Body '{"messages":[{"role":"user","content":"Hola"}]}'
```

#### Bash/Linux/macOS
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hola, ¿cómo estás?"}
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
```

## 🔍 Troubleshooting

### Verificar logs
```bash
docker compose logs lmcache-gptoss
```

### Verificar estado del contenedor
```bash
docker compose ps
docker exec -it lmcache-gptoss bash
```

## 📝 Notas

- Este es un setup básico para LMCache con GPT-OSS
- La integración completa con LMCache se implementará en futuras versiones
- El modelo GPT-OSS se descargará automáticamente cuando se configure la integración completa


