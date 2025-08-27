from typing import List, Union, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configuración del Gateway LiteLLM.
    Carga variables desde .env (si existe) y valida tipos.
    Alineado con backend/core/config.py (Pydantic Settings y env_file).
    """

    # ============================================================================
    # CONFIGURACIÓN DE LA API
    # ============================================================================
    API_TITLE: str = "ORACLE AI: Gateway LiteLLM"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "Gateway LiteLLM para el sistema de Agentes de IA"
    GATEWAY_BASE_PATH: str = "/litellm/oci"
    
    # =============================
    # Logging
    # =============================
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "audit.log"

    # ================================================================== =========
    # CONFIGURACIÓN DE ORACLE CLOUD INFRASTRUCTURE (OCI)
    # ============================================================================
    OCI_PROFILE: str = "DEFAULT"
    OCI_CONFIG_FILE: str = "~/.oci/config"
    OCI_REGION: Optional[str] = None

    # ============================================================================
    # CONFIGURACIÓN DE OCI GENERATIVE AI
    # ============================================================================
    CON_COMPARTMENT_ID: Optional[str] = None
    
    # ============================================================================
    # CONFIGURACIÓN DE SEGURIDAD
    # ============================================================================
    API_KEY: str


    class Config:
        env_file = ".env"
        case_sensitive = True


# Instancia global de configuración
settings = Settings()


