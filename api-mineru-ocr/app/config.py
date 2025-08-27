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
    MINERU_VRAM_PER_WORKER_MB: int = 768

    # Métricas
    METRICS_ENABLED: bool = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()
