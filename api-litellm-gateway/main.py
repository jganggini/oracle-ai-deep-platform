import os
import logging
from fastapi import FastAPI, HTTPException, Depends, Header
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from litellm import acompletion

import oci

from core.config import settings

# Configuración de logging mínima
logging.getLogger().handlers = []
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Crear aplicación FastAPI
app = FastAPI(
	title=settings.API_TITLE,
	version=settings.API_VERSION,
	description=settings.API_DESCRIPTION
)

# Configurar CORS (esta es la forma preferida y más robusta)
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


class ChatMessage(BaseModel):
	role: str
	content: str

class ChatCompletionRequest(BaseModel):
	model: str
	messages: List[ChatMessage]
	temperature: Optional[float] = None


async def verify_api_key(authorization: str = Header(None)):
	"""
	Verifica que el API key sea válido.
	Espera el formato: 'Bearer sk-oracleai-gateway-2024'
	"""
	if not authorization:
		raise HTTPException(
			status_code=401, 
			detail="API key requerida. Use: Authorization: Bearer <api_key>"
		)
	
	try:
		scheme, api_key = authorization.split()
		if scheme.lower() != "bearer":
			raise HTTPException(
				status_code=401, 
				detail="Formato inválido. Use: Authorization: Bearer <api_key>"
			)
		
		if api_key != settings.API_KEY:
			raise HTTPException(
				status_code=401, 
				detail="API key inválida"
			)
		
		return api_key
		
	except ValueError:
		raise HTTPException(
			status_code=401, 
			detail="Formato inválido. Use: Authorization: Bearer <api_key>"
		)


@app.get(f"{settings.GATEWAY_BASE_PATH}/v1/health")
async def proxy_health(api_key: str = Depends(verify_api_key)):
	return {"status": "ok", "message": "API key válida"}

@app.post(f"{settings.GATEWAY_BASE_PATH}/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest, api_key: str = Depends(verify_api_key)):
	# Aceptamos el nombre oficial (xai.grok-4) y resolvemos el proveedor internamente
	model    = req.model if "/" in req.model else f"oci/{req.model}"
	messages = [m.model_dump() for m in req.messages]
	
	# Leer la configuración desde el archivo de configuración
	config_file = os.path.expanduser(settings.OCI_CONFIG_FILE)
	if not os.path.exists(config_file):
		raise FileNotFoundError(f"Archivo de configuración no encontrado: {config_file}")
	
	# Leer la configuración desde el archivo de configuración
	config   = oci.config.from_file(config_file, profile_name=settings.OCI_PROFILE)
	
	# Leer la clave desde el archivo de configuración
	path_key = config.get("key_file")
	with open(path_key, "r") as file:
		key_lines = file.readlines()
	# Elimina la última línea si es exactamente 'OCI_API_KEY\n' o 'OCI_API_KEY', junto con su salto de línea
	if key_lines and key_lines[-1].strip() == "OCI_API_KEY":
		key_lines = key_lines[:-1]
	# Si después de eliminar, la última línea es un salto de línea vacío, también lo quitamos
	if key_lines and key_lines[-1].strip() == "":
		key_lines = key_lines[:-1]
	key = "".join(key_lines)

	resp = await acompletion(	
		model              = model,	
		messages           = messages,
		stream             = False,
		temperature        = req.temperature,
		oci_region         = settings.OCI_REGION,
		oci_user           = config.get("user"),
		oci_fingerprint    = config.get("fingerprint"),	
		oci_tenancy        = config.get("tenancy"),
		oci_key            = key,
		oci_compartment_id = settings.CON_COMPARTMENT_ID,
	)

	return resp