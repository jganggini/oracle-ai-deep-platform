# Gateway LiteLLM

Gateway que expone una API OpenAI-compatible en `/:base_path/v1` (por defecto `/litellm/oci`) usando LiteLLM Proxy como sub-app de FastAPI. Enruta a OCI Generative AI (p.ej. `xai.grok-4`) mediante credenciales OCI.

## 🚀 Pasos de instalación y uso

### 1. Crear entorno virtual (Python 3.11)
Primero asegúrate de tener instalado **Python 3.11**.  
Crea un entorno virtual en la carpeta `.venv`:

```bash
uv venv --python 3.11
```

### 2. Activar el entorno virtual

```bash
# Windows (PowerShell)
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

### 3. Install Requerimientos

```bash
python -m ensurepip --upgrade
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r .\requirements.txt
```

### 3.Variables de entorno (.env)

Ejemplo en `.env`:

```
# ============================================================================
# CONFIGURACIÓN DE ORACLE CLOUD INFRASTRUCTURE (OCI)
# ============================================================================
OCI_CONFIG_FILE=~/.oci/config
OCI_PROFILE=DEFAULT
OCI_REGION=us-chicago-1

# ============================================================================
# CONFIGURACIÓN DE OCI GENERATIVE AI
# ============================================================================
CON_COMPARTMENT_ID=ocid1.compartment.oc1..***

# ============================================================================
# CONFIGURACIÓN DE SEGURIDAD
# ============================================================================
API_KEY=oci-***
```

### 4. Ejecutar

```bash
python start_server.py
```

### 4. Prueba

```python
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(
    base_url    = "http://localhost:4000/litellm/oci/v1",
    api_key     = "oci-***",
    model       = "xai.grok-4",
    temperature = 0
)
print(llm.invoke("Escribe una lista de 5 ideas para cena rápida").content)
```

## 🐳 Despliegue con Docker

### 1) Build de la imagen (Oracle Linux 10-slim)

```bash
cd api-litellm-gateway
docker build -t litellm-gateway:ol10 .
```

Notas:
- Si existe una carpeta `.oci` en el contexto de build, el Dockerfile la copiará a `/home/opc/.oci` con permisos seguros.
- Por seguridad, se recomienda montar `.oci` en runtime como volumen de solo lectura.

### 2) Ejecutar el contenedor montando `.oci`

Windows (PowerShell):
```powershell
docker run -d --rm `
  --name litellm-gateway `
  -p 4000:4000 `
  litellm-gateway:ol10
```

PowerShell (una sola línea):
```powershell
docker run --rm -p 4000:4000 --env-file .env -e OCI_PROFILE=ADRES -e OCI_CONFIG_FILE=/home/opc/.oci/config -v "$env:USERPROFILE\.oci:/home/opc/.oci:ro" --name litellm-gateway litellm-gateway:ol10
```

Linux / macOS:
```bash
docker run --rm -p 4000:4000 \
  --env-file .env \
  -e OCI_PROFILE=ADRES \
  -e OCI_CONFIG_FILE=/home/opc/.oci/config \
  -v $HOME/.oci:/home/opc/.oci:ro \
  --name litellm-gateway litellm-gateway:ol10
```

Variables clave (en `.env` o `-e`):
- `API_KEY` (obligatoria)
- `OCI_PROFILE` (por defecto `ADRES`)
- `OCI_CONFIG_FILE` (por defecto `/home/opc/.oci/config`)
- `OCI_REGION`
- `CON_COMPARTMENT_ID`
### 3) Probar endpoint de salud

```bash
curl -H "Authorization: Bearer <API_KEY>" http://localhost:4000/litellm/oci/v1/health
```
