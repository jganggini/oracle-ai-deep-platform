# Oracle AI: Deep Platform

## Características

- OCR de alta precisión con MinerU (GPU) y API FastAPI
- Monitoreo en tiempo real con Prometheus + Grafana (dashboard provisionado)
- Gateway LMCache (OpenAI-compatible) para agentes/LLMs locales

## 🔧 Requisitos

- Docker Desktop (Windows) con WSL2
- NVIDIA GPU + NVIDIA Container Toolkit (si usarás GPU)
- Puertos por defecto:
  - 8000 (LMCache)
  - 8001 (OCR)
  - 8002 (Prometheus)
  - 8003 (Grafana)

## 🚀 Despliegue rápido (Docker)

### api-mineru-ocr (MinerU OCR)
- Endpoints:
  - `http://localhost:8001/`
  - `http://localhost:8001/metrics`
- Ejecutar:
```bash
cd api-mineru-ocr
docker compose up -d --build
```

### api-monitoring (Prometheus + Grafana)
- Endpoints:
  - Prometheus: `http://localhost:8002/targets`
  - Grafana: `http://localhost:8003/` (admin/admin por defecto)
- Ejecutar:
```bash
cd api-monitoring
docker compose up -d --build
```

### api-lmcache-gpt-oss (LMCache)
- Endpoint: `http://localhost:8000/`
- Ejecutar:
```bash
cd api-lmcache-gpt-oss
docker compose up -d --build
```

## ☸️ Despliegue en Kubernetes (opcional)

```bash
# MinerU OCR
kubectl apply -f api-mineru-ocr/k8s/stack.yaml

# Monitoring (Prometheus + Grafana)
kubectl apply -f api-monitoring/k8s/stack.yaml

# LMCache
kubectl apply -f api-lmcache-gpt-oss/k8s/stack.yaml
```

## 📁 Estructura del repositorio
```
.
├── api-mineru-ocr/        # OCR MinerU (FastAPI)
├── api-monitoring/        # Prometheus + Grafana provisionado
├── api-lmcache-gpt-oss/   # LMCache (OpenAI-compatible)
└── README.md              # Este documento
```

## 🔗 Referencias
- MinerU: https://github.com/opendatalab/MinerU
- Prometheus: https://prometheus.io/
- Grafana: https://grafana.com/
- Docker Compose: https://docs.docker.com/compose/
