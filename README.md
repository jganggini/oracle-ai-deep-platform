[![Issues][issues-shield]][issues-url]
[![LinkedIn][linkedin-shield]][linkedin-url]

<!-- Intro -->
<br />
<div align="center" style="text-align:center;">
  <h1 style="font-size:40px; font-bload"><b style="color:#ec4b42">Oracle AI</b> Deep Agents</h1>
  
  <a style="font-size:large;" href="/src/">👨🏽‍💻 Explore the Code »</a>
  <br/>
  <a href="https://www.youtube.com/@jgangini">🎬 View Demo</a>
  ·
  <a href="https://github.com/jganggini/oracle-ai-deep-platform/issues">💣 Report Bug</a>
  ·
  <a href="https://github.com/jganggini/oracle-ai-deep-platform/pulls">🚀 Request Feature</a>

<!-- Video explicativo de la arquitectura -->
<div align="center" style="margin-bottom: 24px;">
  <video controls>
    <source src="https://github.com/jganggini/oracle-ai-deep-platform/raw/main/_docs/img/architeture-oracle-ai-deep-agents.mp4" type="video/mp4">
    Tu navegador no soporta la reproducción de video.
  </video>
  <br/>
  <i>Video: Arquitectura Oracle AI Deep Agents</i>
</div>
</div>

https://github.com/user-attachments/assets/f3b221a4-eeef-4058-a3db-8cf4bb5de75e



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

## 📚 Development References with Python and Oracle

- MinerU: https://github.com/opendatalab/MinerU
- Prometheus: https://prometheus.io/
- Grafana: https://grafana.com/
- Docker Compose: https://docs.docker.com/compose/

- [**Oracle Cloud Infrastructure Python SDK**](https://github.com/oracle/oci-python-sdk)  
  Repositorio oficial con ejemplos y documentación del SDK de Oracle Cloud Infrastructure para trabajar con servicios como Object Storage, IAM, Database, entre otros.

- [**Conexión a Oracle Database con `oracledb`**](https://python-oracledb.readthedocs.io/en/latest/user_guide/connection_handling.html)  
  Guía oficial para conectar aplicaciones Python a bases de datos Oracle mediante el módulo `oracledb`, incluyendo uso de wallets, conexiones con Autonomous Database y manejo eficiente de sesiones.

- [**ObjectStorageClient - API Reference**](https://oracle-cloud-infrastructure-python-sdk.readthedocs.io/en/latest/api/object_storage/client/oci.object_storage.ObjectStorageClient.html)  
  Documentación de la clase cliente para gestionar objetos y buckets en OCI Object Storage desde Python.

- [**OCI Document Understanding SDK**](https://www.ateam-oracle.com/post/using-oci-document-understanding-sdk-python-functions-document-classification-key-value-extraction)  
  Ejemplos y guía de uso del SDK de Document Understanding para clasificación de documentos, extracción de claves y análisis estructurado de documentos escaneados.

- [**OCI Speech Realtime SDK**](https://github.com/oracle/oci-ai-speech-realtime-python-sdk)  
  SDK oficial para capturar, enviar y transcribir audio en tiempo real con el servicio OCI Speech, ideal para aplicaciones de reconocimiento de voz en vivo.

- [**DBMS_VECTOR_CHAIN para embeddings y chunking**](https://docs.oracle.com/en/database/oracle/oracle-database/23/arpls/dbms_vector_chain1.html)  
  Este paquete PL/SQL permite aplicar operaciones avanzadas con Oracle AI Vector Search, como segmentación de texto (chunking), generación de embeddings, y procesamiento semántico para búsqueda por similitud o híbrida.

- [**DBMS_CLOUD_AI para integración con LLMs (Select AI)**](https://docs.oracle.com/en/database/oracle/oracle-database/23/arpls/dbms_cloud_ai1.html)  
  Paquete PL/SQL que facilita la interacción con modelos de lenguaje natural (LLMs) directamente desde SQL y PL/SQL. Permite generar, explicar y ejecutar consultas a partir de prompts, así como integrarse con múltiples proveedores de IA.

- [**Ejemplo: Configurar Select AI con RAG y GenAI**](https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/doc/select-ai-examples.html#ADBSB-GUID-2FBD7DDB-CAC3-47AF-AB66-17F44C2ADAA4)  
  Tutorial paso a paso para configurar credenciales, conectividad y búsqueda vectorial con integración entre Oracle Autonomous Database, Select AI y GentAI (RAG: Retrieval-Augmented Generation).

- [**LangChain + OCI Generative AI**](https://python.langchain.com/docs/integrations/text_embedding/oci_generative_ai/)  
  Integración nativa de LangChain con los modelos de Oracle Generative AI para realizar embeddings y consultas semánticas sobre texto de manera eficiente desde flujos de procesamiento Python.

---

<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[issues-shield]: https://img.shields.io/github/issues/othneildrew/Best-README-Template.svg?style=for-the-badge
[issues-url]: https://github.com/jganggini/oracle-ai-deep-platform/issues
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://www.linkedin.com/in/jgangini/