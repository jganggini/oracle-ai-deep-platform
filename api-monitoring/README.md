# Stack de Monitoreo: Prometheus + Grafana

## Características

- Setup simple para instalar y ejecutar Prometheus + Grafana con dashboards personalizados usando Docker.
- Configuración embebida y targets dinámicos (file_sd) para descubrimiento flexible.

## 🔧 Configuración

### Puertos y red
- Prometheus expuesto en host: 8002 (contenedor 9090)
- Grafana expuesto en host: 8003 (contenedor 3000)
- Red externa requerida: `docker-mineru_default` (para alcanzar el servicio MinerU)

Si la red no existe aún, créala:
```bash
docker network create docker-mineru_default
```

## 🚀 Instalación Rápida (Docker)

### 1. Construir y ejecutar
```bash
docker compose up -d --build
```

### 2. Siguientes veces
```bash
# Cambios en dashboards (JSON)
docker compose restart grafana

# Cambios en provisioning/datasources
docker compose build grafana
docker compose up -d grafana

# Cambios en prometheus.yml o targets/*.yml
docker compose restart prometheus

# Cambios en docker-compose.yaml
docker compose down
docker compose up -d
```

### 3. Verificar funcionamiento
```bash
# Estado de contenedores
docker compose ps

# Endpoints
curl http://localhost:8002/targets
curl http://localhost:8003/
```

## ☸️ Despliegue en Kubernetes (opcional)

```bash
# Aplicar stack de monitoreo
kubectl apply -f k8s/monitoring-stack.yaml

# Ver pods y services
kubectl get pods -n monitoring
kubectl get svc -n monitoring
# Acceso (según LoadBalancer/IP asignada)
# Prometheus: http://<EXTERNAL-IP>:9090
# Grafana:    http://<EXTERNAL-IP>:3000
```

## 📁 Estructura del Proyecto

```
api-monitoring/
├── docker-compose.yaml     # Prometheus + Grafana (puertos fijos 8002/8003)
├── Dockerfile.grafana      # Imagen personalizada de Grafana
├── prometheus.yml          # Configuración Prometheus (scrape_interval 20s)
├── targets/                # Targets dinámicos (file_sd)
│   └── mineru.yml          # Target para servicio MinerU
├── grafana/
│   ├── dashboards/         # Dashboards personalizados
│   │   └── mineru-overview.json
│   └── provisioning/       # Datasources y dashboards
│       ├── datasources/
│       └── dashboards/
└── k8s/
    └── monitoring-stack.yaml
```

## 📖 Uso

### Endpoints Disponibles

#### Prometheus
- `http://localhost:8002` - Interfaz web de Prometheus
- `http://localhost:8002/targets` - Estado de targets
- `http://localhost:8002/metrics` - Métricas internas

#### Grafana
- `http://localhost:8003` - Dashboard principal (admin/admin por defecto)
- Dashboards y datasource de Prometheus provisionados automáticamente

### Targets Dinámicos (file_sd)

Para agregar nuevos endpoints `/metrics`, crear archivos en `targets/*.yml`. Ejemplo (`targets/mineru.yml`):

```yaml
- labels:
    job: mineru
  targets:
    - host.docker.internal:8001
```

Prometheus recarga la configuración al reiniciar.

## 🐳 Comandos Útiles (Docker)

```bash
# Iniciar en segundo plano
docker compose up -d

# Detener servicios
docker compose down

# Limpiar todo (incluye volúmenes)
docker compose down -v

# Reconstruir e iniciar
docker compose up -d --build

# Estado / logs
docker compose ps
docker compose logs -f prometheus
docker compose logs -f grafana

# Acceso a contenedores
docker exec -it prometheus sh
docker exec -it grafana sh
```

## 📝 Notas

- Prometheus usa file_sd con `targets/*.yml`; el target por defecto de MinerU es `host.docker.internal:8001`.
- El stack Docker se conecta a la red externa `docker-mineru_default` para alcanzar MinerU.
- Intervalo de scrape por defecto (Docker): 20s.
- En Kubernetes, los recursos y puertos son gestionados por `k8s/monitoring-stack.yaml`.

