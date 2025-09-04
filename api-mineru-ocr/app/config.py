from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Para leer desde variables de entorno
    model_config = SettingsConfigDict(env_file_encoding='utf-8')

    # GPU
    GPU_ENABLED: bool = True
    GPU_DEVICE: str = "cuda"
    GPU_BACKEND: str = "pipeline"

    # (Concurrencia eliminada) – ya no se parametriza VRAM ni caps por página

    # Logging / Auditoría
    LOG_LEVEL: str = "INFO" # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FILE: str = "/app/audit.log"

    # Args extra para el CLI de MinerU (por ejemplo para tuning avanzado)
    MINERU_EXTRA_ARGS: str = ""

@lru_cache()
def get_settings() -> Settings:
    return Settings()
