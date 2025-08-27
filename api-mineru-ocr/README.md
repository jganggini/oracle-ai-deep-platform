# Stack de MinerU OCR Docker

## 🚀 Instalación y Uso (Docker Compose)

### 1. Configuración
No se requiere configuración previa. Las variables de entorno están pre-configuradas en `docker-compose.yaml` para usar GPU.

### 2. Construir y Ejecutar
```bash
# Primera vez o después de cambios en el código/dependencias
docker compose up -d --build

# Iniciar el servicio (si ya está construido)
docker compose up -d
```

### 3. Verificar Funcionamiento
```bash
# Verificar estado del contenedor (debe estar "running" o "healthy")
docker compose ps

# Probar endpoints
curl http://localhost:8001/health
curl http://localhost:8001/metrics
```

## ☸️ Despliegue en Kubernetes (OCI OKE)

### 1. Prerrequisitos
- Un clúster de Kubernetes con nodos GPU.
- `kubectl` configurado para apuntar a tu clúster.
- Un secreto de registro (`ocirsecret`) para acceder a tu OCI Container Registry.

### 2. Construir y Subir la Imagen
```bash
# Reemplaza con tus valores de OCI
export REGION="<region>"
export TENANCY="<tenancy-namespace>"
export REPO="<repo>"
export IMAGE_NAME="mineru"
export TAG="latest"

# Construir la imagen
docker build -t $IMAGE_NAME:$TAG -f Dockerfile.mineru .

# Etiquetar la imagen para OCI
docker tag $IMAGE_NAME:$TAG $REGION.ocir.io/$TENANCY/$REPO/$IMAGE_NAME:$TAG

# Subir la imagen a OCI Registry
docker push $REGION.ocir.io/$TENANCY/$REPO/$IMAGE_NAME:$TAG
```

### 3. Desplegar el Stack
El archivo `k8s/stack.yaml` contiene todos los manifiestos necesarios (Namespace, PVCs, Deployment, Service).

```bash
# 1. Edita k8s/stack.yaml y reemplaza los placeholders de la imagen
#    image: <region>.ocir.io/<tenancy-namespace>/repo/mineru:latest

# 2. Aplica el manifiesto
kubectl apply -f k8s/stack.yaml
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
├── app/                  # Lógica de la aplicación FastAPI
├── main.py               # Punto de entrada de la API
├── requirements.txt      # Dependencias Python
├── Dockerfile.mineru     # Dockerfile con soporte GPU
├── docker-compose.yaml   # Orquestación para desarrollo local
├── k8s/
│   └── stack.yaml        # Manifiestos para despliegue en Kubernetes
├── models/               # Directorio para modelos (se monta con volumen)
├── cache/                # Directorio para cache (se monta con volumen)
├── data/                 # Directorio para archivos de entrada (se monta con volumen)
└── _tests/               # Scripts de prueba
    ├── test-ocr.ps1      # PowerShell (Windows)
    └── test-ocr.sh       # Bash (Linux/macOS)
```

## 📖 Uso de la API

### Endpoints Disponibles
- `GET /` - Información del servicio
- `GET /health` - Estado de salud
- `GET /metrics` - Métricas Prometheus
- `POST /ocr` - Procesamiento OCR con campos de formulario

### Ejemplo de OCR (PowerShell)
```powershell
$Form = @{
  file        = Get-Item "C:\file.pdf"
  vram_limit  = "4096"      # MB por proceso
  concurrency = "5"        # páginas en paralelo
}
Invoke-WebRequest -Uri "http://localhost:8001/ocr" -Method POST -Form $Form -OutFile "result.zip"
```

### Ejemplo de OCR (Bash/Linux/macOS)
```bash
curl -X POST "http://localhost:8001/ocr" \
  -F "file=@/ruta/a/doc.pdf" \
  -F "vram_limit=4096" \
  -F "concurrency=5" -o result.zip
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

Tabla de resultados por ejecución:

| Ejecución | Tiempo (s) | Concurrencia | VRAM (MB) |
|-----------|------------|--------------|-----------|
| 2GB/10x Run 1 | 96.73 | 10 | 2048 |
| 2GB/10x Run 2 | 97.07 | 10 | 2048 |
| 2GB/10x Run 3 | 94.28 | 10 | 2048 |
| 4GB/5x Run 1  | 52.66 | 5  | 4096 |
| 4GB/5x Run 2  | 50.61 | 5  | 4096 |
| 4GB/5x Run 3  | 51.70 | 5  | 4096 |
| 8GB/2x Run 1  | 96.01 | 2  | 8192 |
| 8GB/2x Run 2  | 98.62 | 2  | 8192 |
| 8GB/2x Run 3  | 95.13 | 2  | 8192 |

**Notas:**
- El primer run de un escenario puede ser más lento por descarga/caliente de modelos; los siguientes usan caché.
- Hay archivos de ejemplo para pruebas en: [`test.ps1`](./_test/test.ps1).
- Los tiempos varían según hardware, drivers y tipo de documento.

## 🐳 Comandos Útiles (Docker)

```bash
# Iniciar servicio en segundo plano
docker compose up -d

# Detener servicio
docker compose down

# Detener y eliminar volúmenes (limpieza total)
docker compose down -v

# Reconstruir la imagen y reiniciar el servicio
docker compose up -d --build

# Ver estado de los contenedores
docker compose ps

# Ver logs en tiempo real
docker compose logs -f mineru

# Acceder al shell del contenedor
docker exec -it mineru bash

# Ver uso de recursos (CPU, Memoria)
docker stats mineru
```

## ⚡ Optimizaciones Implementadas

### Procesamiento Paralelo por Página
- División automática del PDF en páginas individuales
- Ejecución concurrente de MinerU por página
- Semáforo configurable para controlar concurrencia

### Límites de Hilos por Proceso
- `OMP_NUM_THREADS=1`: Evita contención de OpenMP
- `MKL_NUM_THREADS=1`: Optimiza Intel MKL
- `OPENBLAS_NUM_THREADS=1`: Controla OpenBLAS
- `NUMEXPR_NUM_THREADS=1`: Limita NumExpr

### Gestión Eficiente de Memoria
- VRAM parametrizable para mejor distribución
- Procesamiento por streaming para archivos grandes
- Limpieza automática de archivos temporales

### Estructura de Salida Organizada
- Markdown consolidado con paginación automática
- Imágenes organizadas por página con prefijos
- ZIPs individuales por página para análisis detallado

## 📝 Casos de Uso Recomendados

### Ideal para:
- ✅ PDFs con diversos formatos.
- ✅ GPUs de 4GB o más (escala con VRAM)
- ✅ Procesamiento en lote de documentos
- ✅ Análisis de documentos estructurados
- ✅ Extracción de texto con contexto de página

### Considerar alternativas para:
- ❌ GPUs con <4GB VRAM - reducir concurrencia
- ❌ Tiempo real crítico - usar procesamiento síncrono

## 🔧 Ajustes de Rendimiento

- Aumenta `MINERU_CONCURRENCY` y `VRAM_LIMIT` según recursos.
- Con más GPU/VRAM/CPU, el servicio escala para mayores cargas.

## 🔗 Referencias y Documentación

- [MinerU GitHub](https://github.com/opendatalab/MinerU) - Documentación oficial
- [Docker Compose](https://docs.docker.com/compose/) - Guía de Docker Compose
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/) - Soporte GPU
- [FastAPI](https://fastapi.tiangolo.com/) - Framework web de alto rendimiento

---

**Versión**: 2.0.0-optimized \
**Última actualización**: Agosto 2024.
**Compatibilidad**: CUDA 12.1+, Python 3.10+, Docker 20.10+