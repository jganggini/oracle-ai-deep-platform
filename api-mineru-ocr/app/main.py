import logging
from logging import Filter
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .services.metrics import start_metrics_collector, get_metrics_latest, get_metrics_content_type, init_metric_series
from fastapi import Response
import asyncio as _asyncio
from fastapi import UploadFile, File, Form, Request
from .services.ocr import process_ocr
from pathlib import Path


class SocketSendFilter(Filter):
    def filter(self, record):
        return "socket.send() raised exception." not in record.getMessage()


def create_app() -> FastAPI:
    settings = get_settings()

    # Logging básico + archivo de auditoría
    logging.getLogger().handlers = []
    logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logger = logging.getLogger()
    # Asegurar directorio del archivo de log
    log_path = Path(settings.LOG_FILE)
    if log_path.parent and str(log_path.parent) not in ("", "."):
        log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(str(log_path), mode='a', encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)

    # Filtro para logs de asyncio
    asyncio_logger = logging.getLogger("asyncio")
    asyncio_logger.addFilter(SocketSendFilter())

    # Crear app
    app = FastAPI(title="MinerU OCR Service", version="2.3.0")

    # CORS amplio
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Métricas siempre habilitadas
    start_metrics_collector()
    init_metric_series()

    @app.get("/metrics")
    async def metrics():
        data = await _asyncio.to_thread(get_metrics_latest)
        return Response(content=data, media_type=get_metrics_content_type())

    @app.get("/health")
    async def health():
        return {"status": "healthy"}
        
    # Endpoint /ocr directo llamando a service
    @app.post("/ocr")
    async def ocr_endpoint(
        request: Request,
        file: UploadFile | None = File(None),
        per_worker_mb: int | None = Form(None, ge=256),
        workers_cap: int | None = Form(None, ge=1),
    ):
        return await process_ocr(request, file, per_worker_mb, workers_cap)

    return app


