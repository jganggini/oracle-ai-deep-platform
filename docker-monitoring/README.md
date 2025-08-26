# Stack de Monitoreo: Prometheus + Grafana

## Características

- Setup simple para instalar y ejecutar Prometheus + Grafana con dashboards personalizados usando Docker.
- Configuración embebida en imágenes personalizadas para fácil rebuild y mantenimiento.

## 🔧 Configuración

### Configurar variables de entorno
```bash
cp env.example .env
# Editar .env si es necesario (PROMETHEUS_PORT, GRAFANA_PORT)
```

### Variables de Entorno (.env)
```ini
# Puerto Prometheus
PROMETHEUS_PORT=8002

# Puerto Grafana
GRAFANA_PORT=8003

# Credenciales Grafana
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=admin
```

### Red externa requerida

Este stack se conecta a una red externa (por ejemplo, la del stack OCR) para descubrir servicios con `/metrics`.

- La red externa se parametriza con `EXTERNAL_NETWORK` en `.env`.
- Si el stack OCR ya está arriba, no necesitas crear nada; solo asegúrate de que `EXTERNAL_NETWORK` apunte a su red (p.ej. `docker-ocr_default` o `docker-mineru_default`).
- Si la red no existe aún, créala manualmente antes de levantar este stack:

```bash
docker network create docker-mineru_default
# o personaliza el nombre y usa el mismo en .env: EXTERNAL_NETWORK=tu_red
```

## 🚀 Instalación Rápida

### 1. Construir y ejecutar - Primera vez
```bash
docker compose up -d --build
```

### 2. Siguientes veces
```bash
# Cambios en el dashboard JSON de grafana.
docker compose restart grafana

# Cambios en configuración de Grafana (provisioning, datasources)
docker compose build grafana
docker compose up -d grafana

# Cambios en prometheus.yml (configuración global)
# Cambios en targets dinámicos (targets/*.yml)
docker compose restart prometheus

# Cambios en docker-compose.yaml o variables de entorno
docker compose down
docker compose up -d

# Cambios en plugins o extensiones de Grafana
docker compose build --no-cache grafana
docker compose up -d grafana
```

### 3. Verificar funcionamiento
```bash
# Verificar estado
docker compose ps

# Probar endpoints
curl http://localhost:8002/targets
curl http://localhost:8003/
```

## 📁 Estructura del Proyecto

```
docker-monitoring/
├── docker-compose.yaml     # Configuración Docker (usa .env)
├── Dockerfile.grafana      # Dockerfile personalizado para Grafana
├── env.example            # Variables de entorno de ejemplo
├── prometheus.yml         # Configuración Prometheus
├── targets/               # Targets dinámicos (file_sd)
│   └── mineru.yml        # Target para servicio MinerU
└── grafana/               # Configuración Grafana
    ├── provisioning/      # Datasources y dashboards
    └── dashboards/        # Dashboards personalizados
```

## 📖 Uso

### Endpoints Disponibles

#### Prometheus
- `http://localhost:8002` - Interfaz web de Prometheus
- `http://localhost:8002/targets` - Estado de targets
- `http://localhost:8002/metrics` - Métricas internas

#### Grafana
- `http://localhost:8003` - Dashboard principal (admin/admin)
- Dashboards automáticamente provisionados
- Datasource de Prometheus configurada automáticamente

### Targets Dinámicos (file_sd)

Para agregar nuevos endpoints `/metrics`, crear archivos en `targets/*.yml`. Ejemplo (`targets/mineru.yml`):

```yaml
- labels:
    job: mineru
  targets:
    - host.docker.internal:8001
```

Puedes añadir más archivos y targets sin reiniciar Grafana (Prometheus recarga config al reiniciar).

## 🐳 Comandos Docker Útiles

```bash
# Ver logs
docker compose logs -f

# Reiniciar servicios
docker compose restart

# Parar servicios
docker compose down

# Reconstruir después de cambios
docker compose up -d --build

# Verificar logs específicos
docker compose logs prometheus
docker compose logs grafana

# Verificar estado de contenedores
docker compose ps

# Acceder a contenedores
docker exec -it prometheus sh
docker exec -it grafana sh
```

## 🔄 Reinstalación y Mantenimiento

### Limpiar todo
```bash
docker compose down -v
```

### Reinstalación completa (después de cambios)
```bash
# 1. Detener y limpiar
docker compose down -v

# 2. Reconstruir y levantar
docker compose up -d --build

# 3. Si hay conflictos de nombres, forzar recreación
docker compose up -d --build --force-recreate
```

## ✅ Ventajas del Build Personalizado

- **Fácil rebuild**: `--build` siempre funciona sin problemas de imágenes en uso
- **Configuración embebida**: Dashboards y provisioning van en la imagen
- **Sin volúmenes externos**: Configuración se mantiene en la imagen
- **Reinstalación limpia**: Cambios se aplican inmediatamente

## 📝 Notas

- Prometheus usa configuración file_sd para targets dinámicos
- Grafana se provisiona automáticamente con dashboards y datasources
- El stack se conecta a la red `docker-mineru_default` para acceder a servicios externos
- Las métricas se actualizan cada 20 segundos por defecto

