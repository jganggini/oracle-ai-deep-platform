# MinerU OCR Docker

Servicio Docker optimizado para MinerU OCR con procesamiento paralelo por página, soporte GPU parametrizable por VRAM, y concurrencia configurable para máximo rendimiento.

## 🚀 **Características Principales**

- ✅ **Procesamiento por página**: Divide PDFs y procesa cada página individualmente
- ✅ **Concurrencia configurable**: Escala según GPU/VRAM y CPU disponibles
- ✅ **VRAM parametrizable**: Ajustable por entorno según los recursos del host
- ✅ **Paginación automática**: Genera Markdown con encabezados y marcadores por página
- ✅ **Estructura organizada**: ZIP con `upload.md`, `images/` y `pages/` individuales
- ✅ **Optimizaciones de hilos**: Evita contención con límites de threads por proceso

## 📊 **Pruebas de rendimiento**

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

Notas:
- El primer run de un escenario puede ser más lento por descarga/caliente de modelos; los siguientes usan caché.
- Hay archivos de ejemplo para pruebas en: [`test-ocr.ps1`](./_test/test-ocr.ps1) y [`test-ocr.sh`](./_test/test-ocr.sh).
- Los tiempos varían según hardware, drivers y tipo de documento.

## 🚀 **Instalación Rápida**

### 1. Configurar variables de entorno
```bash
cp env.example .env
# Editar .env para ajustar concurrencia y VRAM según tu GPU
```

### 2. Construir y ejecutar
```bash
# Construir imagen optimizada
docker compose build

# Ejecutar servicio
docker compose up -d
```

### 3. Verificar funcionamiento
```bash
# Verificar estado
docker compose ps

# Probar endpoint principal
curl http://localhost:8001/
```

## 📁 **Estructura del Proyecto**

```
docker-mineru/
├── main.py              # API FastAPI optimizada
├── requirements.txt     # Dependencias Python con PyTorch CUDA
├── Dockerfile.mineru   # Dockerfile con soporte GPU NVIDIA
├── docker-compose.yaml  # Configuración Docker con límites de recursos
├── env.example         # Variables de entorno de ejemplo
├── models/             # Directorio para modelos (se crea automáticamente)
├── cache/              # Directorio para cache (se crea automáticamente)
└── data/               # Directorio para archivos de entrada (se crea automáticamente)
```

## 🔧 **Configuración**

### Variables de Entorno (.env)
```ini
# Puerto principal
MINERU_PORT=8001

# GPU
GPU_ENABLED=true
GPU_DEVICE=cuda
GPU_BACKEND=pipeline

# Optimizaciones de hilos
OMP_NUM_THREADS=1
MKL_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
NUMEXPR_NUM_THREADS=1

# Rutas de caché y modelos
CACHE_DIR=/app/cache
MODEL_PATH=/app/models
```

### **VRAM y concurrencia**

- La aplicación es flexible: ajusta concurrencia y VRAM según tu hardware.
- La concurrencia efectiva depende de la memoria GPU, CPU y velocidad de disco.
- El archivo `env.example` es solo una referencia; no impone límites.

## 📖 **Uso del Servicio**

### **Ejemplo de OCR con campos de formulario (recomendado)**
```powershell
# PowerShell (Windows)
$Form = @{
  file        = Get-Item "C:\file.pdf"
  vram_limit  = "2048"      # MB por proceso
  concurrency = "10"        # páginas en paralelo
  use_gpu     = "true"
  device      = "cuda"
  backend     = "pipeline"
}
Invoke-WebRequest -Uri "http://localhost:8001/ocr" -Method POST -Form $Form -OutFile "D:\Downloads\ocr_result.zip"
```

```bash
# Bash/Linux/macOS
curl -X POST "http://localhost:8001/ocr" \
  -F "file=@/ruta/a/doc.pdf" \
  -F "vram_limit=2048" \
  -F "concurrency=10" \
  -F "use_gpu=true" \
  -F "device=cuda" \
  -F "backend=pipeline" -o upload.zip
```

### **Ejemplo alternativo con Invoke-WebRequest (PowerShell 7+)**
```powershell
$Form = @{
  file        = Get-Item "C:\doc.pdf"
  vram_limit  = "2048"
  concurrency = "10"
  use_gpu     = "true"
  device      = "cuda"
  backend     = "pipeline"
}
$sw=[System.Diagnostics.Stopwatch]::StartNew()
Invoke-WebRequest -Uri "http://localhost:8001/ocr" -Method POST -Form $Form -OutFile "D:\Downloads\ocr_result.zip"
$sw.Stop()
Write-Output ("Procesado en " + [Math]::Round($sw.Elapsed.TotalSeconds,2) + " s")
```

### **Estructura del ZIP Resultante**
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

### **Formato del Markdown Generado**
```markdown
## Página 1 <a id="p1"></a>

# Título del documento

Contenido del primer párrafo [p1](#p1)

## Página 2 <a id="p2"></a>

Contenido de la segunda página [p2](#p2)
```

## 🐳 **Comandos Docker Útiles**

```bash
# Ver logs en tiempo real
docker compose logs -f

# Reiniciar servicio
docker compose restart

# Parar servicio
docker compose down

# Reconstruir después de cambios
docker compose up -d --build

# Ejecutar con configuración personalizada
MINERU_CONCURRENCY=3 VRAM_LIMIT=2048 docker compose up -d

# Verificar uso de recursos
docker stats mineru-ocr
```

## 🔍 **Troubleshooting y Monitoreo**

### **Verificar logs del servicio**
```bash
docker compose logs mineru
```

### **Verificar estado del contenedor**
```bash
docker compose ps
docker exec -it mineru-ocr bash
```

### **Verificar GPU y VRAM**
```bash
# Dentro del contenedor
nvidia-smi
python3 -c "import torch; print(f'CUDA disponible: {torch.cuda.is_available()}'); print(f'VRAM total: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB')"
```

### **Monitorear rendimiento**
```bash
# Ver uso de CPU y memoria
docker stats mineru-ocr

# Ver logs de procesamiento
docker compose logs -f --tail=100
```

## ⚡ **Optimizaciones Implementadas**

### **1. Procesamiento Paralelo por Página**
- División automática del PDF en páginas individuales
- Ejecución concurrente de MinerU por página
- Semáforo configurable para controlar concurrencia

### **2. Límites de Hilos por Proceso**
- `OMP_NUM_THREADS=1`: Evita contención de OpenMP
- `MKL_NUM_THREADS=1`: Optimiza Intel MKL
- `OPENBLAS_NUM_THREADS=1`: Controla OpenBLAS
- `NUMEXPR_NUM_THREADS=1`: Limita NumExpr

### **3. Gestión Eficiente de Memoria**
- VRAM parametrizable para mejor distribución
- Procesamiento por streaming para archivos grandes
- Limpieza automática de archivos temporales

### **4. Estructura de Salida Organizada**
- Markdown consolidado con paginación automática
- Imágenes organizadas por página con prefijos
- ZIPs individuales por página para análisis detallado

## 📝 **Casos de Uso Recomendados**

### **Ideal para:**
- ✅ PDFs de 10-50 páginas
- ✅ GPUs de 4GB o más (escala con VRAM)
- ✅ Procesamiento en lote de documentos
- ✅ Análisis de documentos estructurados
- ✅ Extracción de texto con contexto de página

### **Considerar alternativas para:**
- ❌ PDFs muy largos (>100 páginas) - usar procesamiento por lotes
- ❌ GPUs con <4GB VRAM - reducir concurrencia
- ❌ Tiempo real crítico - usar procesamiento síncrono

## 🔧 **Ajustes de Rendimiento**

- Aumenta `MINERU_CONCURRENCY` y `VRAM_LIMIT` según recursos.
- Con más GPU/VRAM/CPU, el servicio escala para mayores cargas.

## 🔗 **Referencias y Documentación**

- [MinerU GitHub](https://github.com/opendatalab/MinerU) - Documentación oficial
- [Docker Compose](https://docs.docker.com/compose/) - Guía de Docker Compose
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/) - Soporte GPU
- [FastAPI](https://fastapi.tiangolo.com/) - Framework web de alto rendimiento

## 📈 **Roadmap Futuro**

- [ ] Soporte para procesamiento por lotes de múltiples PDFs
- [ ] Métricas de rendimiento en tiempo real
- [ ] Cache inteligente de modelos para reutilización
- [ ] API para monitoreo de recursos GPU/CPU
- [ ] Soporte para otros formatos de entrada (TIFF, PNG, etc.)

---

**Versión**: 2.0.0-optimized  
**Última actualización**: Diciembre 2024  
**Compatibilidad**: CUDA 12.1+, Python 3.10+, Docker 20.10+
