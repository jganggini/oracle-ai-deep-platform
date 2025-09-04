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

  <img src="../_docs/img/MinerU-logo.png" alt="opendatalab%2FMinerU | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/>
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
- Optimización para GPUs.

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

💡 `Notas`: Se requiere de NVIDIA Container Toolkit instalado para usar GPU.

🚨 `Parámetros` → [config.py](/api-mineru-ocr/app/config.py):

- `GPU_ENABLED (true)`: habilita GPU; usa `false` para CPU.
- `GPU_DEVICE ("cuda")`: dispositivo de cómputo (`cuda`, `cuda:0` o `cpu`).
- `GPU_BACKEND ("pipeline")`: backend de ejecución de MinerU.
- `LOG_LEVEL ("INFO")`: nivel de log (DEBUG/INFO/WARN/ERROR).
- `LOG_FILE ("/app/audit.log")`: ruta del log persistente.
- `MINERU_EXTRA_ARGS ("")`: flags adicionales (avanzado). Nota: el servicio fuerza `--make content_list`.

#### Paso 3: ☸️ Despliegue en Kubernetes (OCI OKE)

- Prerrequisitos
  - Un clúster de Kubernetes con nodos GPU.
  - `kubectl` configurado para apuntar a tu clúster.
  - Un secreto de registro (`ocirsecret`) para acceder a tu OCI Container Registry.

- Construir y Subir la Imagen

  ```bash
  # Construir la imagen
  docker build -t mineru-ocr:latest -f Dockerfile.mineru .

  # Etiquetar la imagen para OCI (reemplaza con tus valores)
  docker tag mineru-ocr:latest <region>.ocir.io/<tenancy-namespace>/<repo>/mineru-ocr:latest

  # Subir la imagen a OCI Registry
  docker push <region>.ocir.io/<tenancy-namespace>/<repo>/mineru-ocr:latest
  ```

- Desplegar el Stack
  El archivo `manifest.mineru.yaml` contiene los manifiestos necesarios (Namespace, Deployment, Service).

  ```bash
  # Reemplaza los placeholders de la imagen:
  # <region>.ocir.io/<tenancy-namespace>/repo/mineru:latest
  kubectl apply -f manifest.mineru.yaml
  ```

- Verificar el Despliegue

  ```bash
  # Verificar que el pod esté corriendo en el namespace 'mineru'
  kubectl get pods -n mineru

  # Obtener la IP externa del LoadBalancer
  kubectl get svc -n mineru

  # Una vez que la IP externa esté asignada, puedes acceder al servicio:
  # http://<IP-EXTERNA>:8001/health
  ```

- Limpieza

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
- `GET /health` - Estado de salud
- `GET /metrics` - Métricas Prometheus
- `POST /ocr` - Procesamiento OCR (multipart: `file`)

### Ejemplo (PowerShell)
```powershell
$Form = @{ file = Get-Item "C:\doc.pdf" }
Invoke-WebRequest -Uri "http://localhost:8001/ocr" -Method POST -Form $Form -OutFile "result.zip"
```

### Ejemplo (Bash/Linux/macOS)
```bash
curl -X POST "http://localhost:8001/ocr" \
  -F "file=@/ruta/a/doc.pdf" \
  -o result.zip
```

### Estructura del ZIP Resultante
```
upload.zip
├── upload.md              # Markdown consolidado con paginación por página y párrafo
├── content_list.json      # Estructura CONTENT_LIST (el servicio la incluye siempre)
└── images/                # Imágenes referenciadas en el markdown
    ├── img_1.jpg
    ├── img_2.jpg
    └── ...
```

### Nombre del archivo de salida

- El ZIP devuelto por el endpoint se nombra automáticamente con el patrón:

  ```
  <nombre_base_entrada>_P####.zip
  ```

  - Ejemplos: `Factura2024_P0015.zip` (15 páginas), `Reporte_P0100.zip` (100 páginas).

### Paginación en el Markdown

- Encabezado por página: `## Página N <a id="pN"></a>`
- En cada párrafo de texto, imagen y tabla se añade un enlace corto a su página: `[pN](#pN)`

### Formato del Markdown Generado
```markdown
## Página 1 <a id="p1"></a>

# Título del documento

Contenido del primer párrafo [p1](#p1)

## Página 2 <a id="p2"></a>

Contenido de la segunda página [p2](#p2)
```


## ✅ Pruebas locales

- Mínima (un archivo): `_tests/test.ps1`
- Múltiples archivos (en `_tests/files`): `_tests/test-multi-docs.ps1`
  - Genera un ZIP por archivo en `_tests/result/<archivo>.zip`
  - Muestra progreso [i/N], tiempo por archivo, páginas detectadas y tiempo total en `hh:mm:ss`
  - Línea de salida por archivo (ejemplo):

    ```
    [OK][time=73.69s][pag=15][out=D:\dev\poc\oci.adres.sia\api-mineru-ocr\_tests\result\E54010325120549R001402207700_P0015.zip]
    ```

### Notas y solución de problemas

- MinerU requiere extensión `.pdf` en minúsculas. El servicio normaliza automáticamente `.PDF` → `.pdf` al recibir el archivo.
- El servicio fuerza `--make content_list` para obtener `content_list.json`.
- No dependemos del ZIP generado por MinerU: si no existe, se usa la salida local (`out_doc/.../ocr`) para construir el resultado y empaquetar el ZIP final del servicio.

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


