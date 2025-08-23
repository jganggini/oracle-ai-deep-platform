from __future__ import annotations
import asyncio
from fastapi import FastAPI, Response
from .config import get_settings
from .metrics import start_metrics_collector, get_metrics_latest, get_metrics_content_type, init_metric_series
from .ocr.endpoints import router as ocr_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="MinerU OCR Service", version="2.2.0-prom")
    app.include_router(ocr_router)

    if settings.metrics_enabled:
        start_metrics_collector()
        init_metric_series()

        @app.get("/metrics")
        async def metrics():
            data = await asyncio.to_thread(get_metrics_latest)
            return Response(content=data, media_type=get_metrics_content_type())

    @app.get("/")
    async def root():
        return {
            "service": "MinerU OCR",
            "version": "2.2.0-prom",
            "gpu_enabled": settings.gpu_enabled,
            "device": settings.gpu_device,
            "backend": settings.gpu_backend,
        }

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    return app
