# Oracle AI: Deep Platform

Resumen de los servicios Docker incluidos en este repositorio.

## docker-mineru (OCR)
- Servicio FastAPI para OCR basado en MinerU
- Procesamiento por página con concurrencia configurable por request (form-data)
- Salida ZIP con `upload.md`, `images/` y `pages/`
- GPU opcional (CUDA), límites de hilos para estabilidad

Enlaces y documentación:
- Carpeta: `./docker-mineru`
- Guía completa: `./docker-mineru/README.md`

Inicio rápido:
```bash
cd docker-mineru
cp env.example .env
# Ejecutar
docker compose up -d --build
```

Ejemplo de invocación (curl.exe, Windows):
```powershell
curl.exe -X POST "http://localhost:8001/ocr" ^
  -F "file=@C:\doc.pdf" ^
  -F "vram_limit=2048" ^
  -F "concurrency=10" ^
  -F "use_gpu=true" ^
  -F "device=cuda" ^
  -F "backend=pipeline" ^
  --output "D:\Downloads\ocr_result.zip"
```

## docker-lmcache-gpt-oss (Gateway LLM)
- Composición orientada a LMCache compatible con API OpenAI
- Integración con modelos OpenAI-compat (p. ej., GPT-OSS vía Ollama/VLLM)
- Ideal como caché/gateway para agentes y RAG

Enlaces y documentación:
- Carpeta: `./docker-lmcache-gpt-oss`
- Guía: `./docker-lmcache-gpt-oss/README.md`

Inicio rápido (referencial):
```bash
cd docker-lmcache-gpt-oss
cp env.example .env
# Ejecutar
docker compose up -d --build
```

## Notas generales
- Requisitos: Docker Desktop (Windows) con soporte WSL2 y NVIDIA Container Toolkit si usas GPU
- Ajusta variables en `.env` por servicio; en MinerU, `vram_limit` y `concurrency` se envían por formulario en cada request
- Pruebas: ver scripts en `docker-mineru/_test/` para medir rendimiento

## Licencias y créditos
- MinerU: ver repositorio oficial de OpenDataLab
- LMCache: ver proyecto LMCache
- Este repositorio agrega orquestación y utilidades sobre dichos proyectos
