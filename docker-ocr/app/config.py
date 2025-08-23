from __future__ import annotations
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # API
    api_port: int = int(os.getenv("MINERU_PORT", "8000"))

    # GPU
    gpu_enabled: bool = True
    gpu_device: str = os.getenv("GPU_DEVICE", "cuda")
    gpu_backend: str = os.getenv("GPU_BACKEND", "pipeline")

    # Concurrencia
    vram_per_worker_mb: int = max(256, int(os.getenv("MINERU_VRAM_PER_WORKER_MB", "768")))

    # Métricas
    metrics_enabled: bool = os.getenv("METRICS_ENABLED", "true").lower() == "true"
    metrics_port: int = int(os.getenv("METRICS_PORT", "8002"))

    # Rutas
    model_path: str = os.getenv("MODEL_PATH", "/app/models")
    cache_dir: str = os.getenv("CACHE_DIR", "/app/cache")


def get_settings() -> Settings:
    return Settings()
