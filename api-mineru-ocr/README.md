[![Issues][issues-shield]][issues-url]
[![LinkedIn][linkedin-shield]][linkedin-url]

<br />
<div align="center" style="text-align:center;">
  
  <a style="font-size:large;" href="/src/">👨🏽‍💻 Explore the Code »</a>
  <br/>
  <a href="https://www.youtube.com/watch?v=KC23zRaC-_U&list=PLMUWTQHw13gZ54wEx2XRxWE5is4B12szC">🎬 View Demo</a>
  ·
  <a href="https://github.com/jganggini/oracle-ai-deep-platform/issues">💣 Report Bug</a>
  ·
  <a href="https://github.com/jganggini/oracle-ai-deep-platform/pulls">🚀 Request Feature</a>

  <a href="https://youtu.be/5dilnUUcgQE?si=V4t6ImWXS-aJSYEl" target="_blank">
    <img src="../_docs/img/MinerU-logo.png">
  </a>
</div>
<br />

## 📄 Contents

MinerU es una herramienta avanzada que convierte archivos PDF en formatos legibles por máquina, como markdown y JSON, permitiendo la extracción sencilla de información a cualquier formato requerido. MinerU nació durante el pre-entrenamiento de InternLM, con el objetivo de resolver problemas de conversión de símbolos en literatura científica y contribuir al desarrollo tecnológico en la era de los grandes modelos de lenguaje.

**Este proyecto integra MinerU y añade una funcionalidad clave:**  
Cada párrafo y página del PDF procesado se numera automáticamente en el resultado markdown, facilitando la referencia y localización precisa del contenido extraído. Esto es especialmente útil para tareas de análisis, revisión o trazabilidad de información en documentos extensos.

**Ventajas principales:**
- Extracción estructurada de texto y tablas desde PDFs complejos.
- Numeración automática de páginas y párrafos en el markdown generado.
- Organización clara del contenido para búsquedas y referencias rápidas.
- Soporte para procesamiento concurrente y optimización para GPUs.

Para más información técnica, revisa la [documentación oficial de MinerU](https://github.com/opendatalab/MinerU).

---

#### Paso 1: Construir la imagen

```bash
docker build -t mineru-ocr:latest -f Dockerfile.mineru .
```

#### Paso 2: Desplegar

- PowerShell (Windows):
  ```powershell
  # true=GPU, false=CPU
  docker run --rm -d `
    --gpus all `
    -e GPU_ENABLED=true `
    -p 8001:8000 `
    -v ${PWD}:/app `
    --name mineru `
    mineru-ocr:latest
  ```

- Bash (Linux/macOS o Git Bash/WSL en Windows):
  ```bash
  # true=GPU, false=CPU
  docker run --rm -d \
    --gpus all \
    -e GPU_ENABLED=true \
    -p 8001:8000 \
    -v "$PWD":/app \
    --name mineru \
    mineru-ocr:latest
  ```

💡 `Notas`:
- Se requiere de NVIDIA Container Toolkit instalado para usar GPU.

🚨 `Parámetros` → [Dockerfile.mineru](/api-mineru-ocr/Dockerfile.mineru):

- `OMP_NUM_THREADS=1`: límite de hilos para librerías basadas en OpenMP. Evita sobre-suscripción de CPU.
- `MKL_NUM_THREADS=1`: límite de hilos de Intel MKL para operaciones numéricas.
- `OPENBLAS_NUM_THREADS=1`: controla el paralelismo de OpenBLAS.
- `NUMEXPR_NUM_THREADS=1`: fija los hilos de NumExpr. Mantenerlos en 1 reduce contención cuando ya hay concurrencia por páginas.

ℹ️ Estos límites están pensados para entornos con múltiples procesos concurrentes (una página por proceso). Si ejecutas sólo 1 worker y necesitas máximo rendimiento en CPU, puedes incrementarlos, pero monitoriza la latencia y la contención.

🚨 `Parámetros` → [config.py](/api-mineru-ocr/app/config.py):

- `GPU_ENABLED (true)`: habilita el uso de GPU. Usa `false` para forzar CPU.
- `GPU_DEVICE ("cuda")`: dispositivo de cómputo (p.ej., `cuda`, `cuda:0` o `cpu`).
- `GPU_BACKEND ("pipeline")`: backend de ejecución de MinerU.
- `MINERU_VRAM_PER_WORKER_MB (1536)`: VRAM por worker en MB. Menor = más concurrencia; mayor = más estabilidad.
- `MINERU_WORKERS_CAP (6)`: tope superior de workers simultáneos tras cálculo por VRAM/CPU.
- `MINERU_VRAM_OVERHEAD_MB (512)`: overhead de VRAM por proceso para calcular concurrencia segura.
- `MINERU_PAGE_TIMEOUT_MS (180000)`: timeout por página (ms) para abortar procesos colgados.
- `MINERU_RAMP_DELAY_MS (300)`: retardo incremental (ms) entre lanzamientos; suaviza picos de inicialización.
- `LOG_LEVEL ("INFO")`: nivel de log global (DEBUG/INFO/WARN/ERROR).
- `LOG_FILE ("/app/audit.log")`: ruta del log persistente dentro del contenedor.
- `MINERU_VERBOSE_STAGES (false)`: logs de progreso de etapas (OCR-det/rec/etc.).
- `MINERU_LOG_DETAILED (false)`: logs detallados por página (timings, uso de recursos).
- `MINERU_EXTRA_ARGS ("")`: flags adicionales para pasar al CLI de MinerU (avanzado).

🧮 `Cálculos`:

- Variables usadas:

  - VRAM total detectada: `total_vram_mb`
  - VRAM por worker: `per_worker_mb` (form-data) o `MINERU_VRAM_PER_WORKER_MB` (default)
  - Overhead por proceso: `MINERU_VRAM_OVERHEAD_MB`
  - Núcleos CPU: `cpu_cores`
  - Límite superior opcional: `workers_cap` (form-data) o `MINERU_WORKERS_CAP`

Fórmulas:

  ```math
  \text{vram\_per\_proc} = \text{per\_worker\_mb} + \text{MINERU\_VRAM\_OVERHEAD\_MB}
  ```

  ```math
  \text{allowed\_by\_vram} = \begin{cases}
  \left\lfloor \dfrac{\text{total\_vram\_mb}}{\text{vram\_per\_proc}} \right\rfloor & \text{→ si GPU\_ENABLED} \\
  1 & \text{→ si CPU}
  \end{cases}
  ```

  ```math
  \text{prelim} = \max\big(1,\; \min(\text{allowed\_by\_vram},\; \text{cpu\_cores})\big)
  ```

  ```math
  \text{max\_workers} = \begin{cases}
  \min(\text{prelim},\; \text{cap}) & \text{→ si cap existe} \\
  \text{prelim} & \text{→ en otro caso}
  \end{cases}
  ```

Ejemplo:

```math
\text{total\_vram\_mb}=24576,\; \text{per\_worker\_mb}=1536
```
```math
\text{MINERU\_VRAM\_OVERHEAD\_MB}=512
```
```math
\text{vram\_per\_proc}=1536+512=2048
```
```math
\text{allowed\_by\_vram}=\left\lfloor \dfrac{24576}{2048} \right\rfloor=12
```
```math
\text{cpu\_cores}=8 \Rightarrow \text{prelim}=\min(12,8)=8
```
```math
\text{cap}=6 \Rightarrow \text{max\_workers}=\min(8,6)=6
```

💡 `Notas`:
- `MINERU_RAMP_DELAY_MS` solo escalona los lanzamientos (suaviza picos); no cambia `max_workers`.
- Si `GPU_ENABLED=false`, se fuerza `allowed_by_vram = 1` y la concurrencia queda limitada por CPU y `cap`.

#### Paso 3: ☸️ Despliegue en Kubernetes (OCI OKE)

### 1. Prerrequisitos
- Un clúster de Kubernetes con nodos GPU.
- `kubectl` configurado para apuntar a tu clúster.
- Un secreto de registro (`ocirsecret`) para acceder a tu OCI Container Registry.

### 2. Construir y Subir la Imagen

```bash
# Construir la imagen
docker build -t mineru-ocr:latest -f Dockerfile.mineru .

# Etiquetar la imagen para OCI (reemplaza con tus valores)
docker tag mineru-ocr:latest <region>.ocir.io/<tenancy-namespace>/<repo>/mineru-ocr:latest

# Subir la imagen a OCI Registry
docker push <region>.ocir.io/<tenancy-namespace>/<repo>/mineru-ocr:latest
```

### 3. Desplegar el Stack
El archivo `manifest.mineru.yaml` contiene los manifiestos necesarios (Namespace, Deployment, Service).

```bash
# Reemplaza los placeholders de la imagen:
# <region>.ocir.io/<tenancy-namespace>/repo/mineru:latest
kubectl apply -f manifest.mineru.yaml
```

### 4. Verificar el Despliegue
```bash
# Verificar que el pod esté corriendo en el namespace 'mineru'
kubectl get pods -n mineru

# Obtener la IP externa del LoadBalancer
kubectl get svc -n mineru

# Una vez que la IP externa esté asignada, puedes acceder al servicio:
# http://<IP-EXTERNA>:8001/health
```

### 5. Limpieza
```bash
kubectl delete -f k8s/stack.yaml
```

## 📁 Estructura del Proyecto

```
api-mineru-ocr/
├── app/                      # Código de la aplicación FastAPI
│   ├── main.py               # Inicializa app + logging persistente
│   ├── start_server.py       # Uvicorn entry (app.start_server:app)
│   ├── config.py             # Configuración (pydantic)
│   ├── metrics.py            # Métricas Prometheus
│   └── services/
│       ├── ocr.py            # Lógica de OCR como servicio (process_ocr)
│       ├── mineru.py         # Wrapper CLI MinerU + extracción/MD
│       └── metrics.py        # Métricas Prometheus
├── Dockerfile.mineru         # Imagen
├── manifest.mineru.yaml      # Manifiesto de despliegue OKE
├── requirements.txt          # Dependencias Python
├── README.md                 # Documentación
└── _tests/                   # Ejemplos y pruebas locales
    ├── test.ps1              # Ejecución mínima (PowerShell)
    ├── test-performance.ps1  # Benchmark simple
    ├── test-factura.pdf      # PDF de muestra
    └── result/               # Salidas local
```

## 📖 Uso de la API

### Endpoints Disponibles
- `GET /` - Información del servicio
- `GET /health` - Estado de salud
- `GET /metrics` - Métricas Prometheus
- `POST /ocr` - Procesamiento OCR con campos de formulario

### Ejemplo (PowerShell)
```powershell
# Todos los parámetros del endpoint /ocr vía multipart/form-data
$Form = @{
  file          = Get-Item "C:\doc.pdf"  # archivo PDF
  per_worker_mb = "1536"                  # opcional (>=256)
  workers_cap   = "6"                     # opcional (>=1)
}
Invoke-WebRequest -Uri "http://localhost:8001/ocr" -Method POST -Form $Form -OutFile "result.zip"
```

### Ejemplo (Bash/Linux/macOS)
```bash
curl -X POST "http://localhost:8001/ocr" \
  -F "file=@/ruta/a/doc.pdf" \
  -F "per_worker_mb=1536" \
  -F "workers_cap=6" \
  -o result.zip
```

### Estructura del ZIP Resultante
```
upload.zip
├── upload.md              # Markdown consolidado con paginación
├── images/                # Imágenes extraídas por página
│   ├── p1_imagen1.jpg
│   ├── p2_imagen2.jpg
│   └── ...
└── pages/                 # ZIPs individuales por página
    ├── page_0001.zip
    ├── page_0002.zip
    └── ...
```

### Formato del Markdown Generado
```markdown
## Página 1 <a id="p1"></a>

# Título del documento

Contenido del primer párrafo [p1](#p1)

## Página 2 <a id="p2"></a>

Contenido de la segunda página [p2](#p2)
```

## 📊 Pruebas de Rendimiento

Host de referencia:
- GPU: NVIDIA 24 GB (NVIDIA Container Toolkit)
- CPU: 16 vCPU
- Disco: NVMe

Escenarios (parámetros enviados por API):

| per_worker_mb | cap | Run #1 (s) | Run #2 (s) | Run #3 (s) | Promedio (s) |
|---------------|-----|------------|------------|------------|--------------|
| 512           | 6   | 66.09      | 60.09      | 54.41      | 60.20        |
| 768           | 6   | 54.71      | 54.84      | 54.58      | 54.71        |
| 1024          | 6   | 55.43      | 54.34      | 55.23      | 55.00        |

Notas:
- En este equipo, `per_worker_mb=768` y `cap=6` dio el mejor promedio.
- Ajusta `workers_cap` según vCPU/IO. Si CPU se satura, baja el cap.
- La concurrencia efectiva interna utiliza VRAM total y `per_worker_mb`.

### Pruebas locales rápidas

- Ejemplo mínimo (PowerShell):
```powershell
cd .\_tests
# corre varios escenarios (per_worker_mb y workers_cap)
test-performance.ps1
# usa per_worker_mb=1536 y workers_cap=6; guarda result.zip
test.ps1  
```

💡 `Notas`: Si ves en los ZIP el mensaje `{ "detail": "VRAM insuficiente para 1 worker ..." }`, verifica que el contenedor tiene acceso a GPU (usa `--gpus all` y `-e GPU_ENABLED=true`), o ejecuta en CPU con `-e GPU_ENABLED=false`.

## 🐳 Comandos Útiles

```bash
# Ver logs en tiempo real
docker logs -f mineru

# Ver archivo de log persistente (si mapeaste -v "$PWD":/app)
tail -f app/audit.log

# Acceder al shell del contenedor
docker exec -it mineru bash

# Ver uso de recursos (CPU, Memoria)
docker stats mineru
```
## 📝 Casos de Uso Recomendados

### Ideal para:
- ✅ PDFs con diversos formatos.
- ✅ GPUs de 4GB o más (escala con VRAM)
- ✅ Procesamiento en lote de documentos
- ✅ Análisis de documentos estructurados
- ✅ Extracción de texto con contexto de página

### Considerar alternativas para:
- ❌ GPUs con <4GB VRAM - aumentar per_worker_mb
- ❌ Tiempo real crítico - usar procesamiento síncrono

## 🔧 Ajustes de Rendimiento

- Controla la eficiencia con `per_worker_mb`: valores más bajos = más workers paralelos, valores más altos = más estabilidad por worker.
- El servicio detecta automáticamente la VRAM total y calcula la concurrencia óptima: `floor(total_vram_mb / per_worker_mb)`.
- Ajusta `per_worker_mb` según tu GPU: 512-768 MB para estabilidad, 1024+ MB para máxima estabilidad.

## 📚 Development References

- [MinerU GitHub](https://github.com/opendatalab/MinerU) - Documentación oficial
- [Docker Compose](https://docs.docker.com/compose/) - Guía de Docker Compose
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/) - Soporte GPU
- [FastAPI](https://fastapi.tiangolo.com/) - Framework web de alto rendimiento

<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[issues-shield]: https://img.shields.io/github/issues/othneildrew/Best-README-Template.svg?style=for-the-badge
[issues-url]: https://github.com/jganggini/oracle-ai-deep-platform/issues
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://www.linkedin.com/in/jgangini/


