# Oracle AI: Deep Platform

## Características

- OCR de alta precisión con MinerU (GPU) y API FastAPI
- Monitoreo en tiempo real con Prometheus + Grafana (dashboard provisionado)
- LMCache gateway (OpenAI-compatible) para futuros agentes/LLMs

## 🔧 Requisitos

- Docker Desktop (Windows) con WSL2
- NVIDIA GPU + NVIDIA Container Toolkit (si usarás GPU)
- Puertos por defecto: 8001 (OCR), 8002 (Prometheus), 8003 (Grafana)

## 🚀 Flujo de despliegue recomendado

### docker-lmcache (LLM para Agentes)

- http://localhost:8000/

### docker-ocr (MinerU OCR)

- `http://localhost:8001/`
- `http://localhost:8001/metrics`

### docker-monitoring (Prometheus + Grafana)

- Prometheus: `http://localhost:8002/targets`
- Grafana: `http://localhost:8003/` (admin/admin)


## 📁 Estructura del repositorio
```
.
├── docker-ocr/           # OCR MinerU (FastAPI)
├── docker-monitoring/    # Prometheus + Grafana provisionado
├── docker-lmcache/       # LMCache (opcional)
└── README.md             # Este documento
```

## 🔗 Referencias
- MinerU: https://github.com/opendatalab/MinerU
- Prometheus: https://prometheus.io/
- Grafana: https://grafana.com/
- Docker Compose: https://docs.docker.com/compose/
