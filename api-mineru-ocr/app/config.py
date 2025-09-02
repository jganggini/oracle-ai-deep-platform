from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Para leer desde variables de entorno
    model_config = SettingsConfigDict(env_file_encoding='utf-8')

    # GPU
    GPU_ENABLED: bool = True
    GPU_DEVICE: str = "cuda"
    GPU_BACKEND: str = "pipeline"

    # Concurrencia
    # Variables dependientes de la GPU (expuestas por API/test)
    MINERU_VRAM_PER_WORKER_MB: int = 1536
    MINERU_WORKERS_CAP: int | None = 6
    
    # Parámetros fijos
    MINERU_VRAM_OVERHEAD_MB: int = 512

    # Control de estabilidad
    MINERU_PAGE_TIMEOUT_MS: int = 180000   # Tiempo máx por página (ms)
    MINERU_RAMP_DELAY_MS: int = 300        # Espaciado entre lanzamientos por página (ms)

    # Logging / Auditoría
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "/app/audit.log"
    MINERU_VERBOSE_STAGES: bool = False   # Logs detallados por etapa (OCR-det/rec/etc.)
    MINERU_LOG_DETAILED: bool = False     # Logs detallados por página

    # Args extra para el CLI de MinerU (por ejemplo para tuning avanzado)
    MINERU_EXTRA_ARGS: str = ""

@lru_cache()
def get_settings() -> Settings:
    return Settings()
