FROM vllm/vllm-openai:latest

# Copiar configuración de LMCache dentro de la imagen
COPY backend_cpu.yaml /app/backend_cpu.yaml

# Variables de entorno para LMCache
ENV LMCACHE_CONFIG_FILE=/app/backend_cpu.yaml \
    LMCACHE_USE_EXPERIMENTAL=True

# Puerto por defecto del API OpenAI-compatible de vLLM
EXPOSE 8000

# La imagen base ya define el ENTRYPOINT del servidor OpenAI.
# Establecemos argumentos por defecto (se pueden sobreescribir al ejecutar "docker run ... <args>")
CMD ["--model", "openai/gpt-oss-20b", \
    "--max-model-len", "32768", \
    "--disable-hybrid-kv-cache-manager", \
    "--kv-transfer-config", "{\"kv_connector\":\"LMCacheConnectorV1\",\"kv_role\":\"kv_both\"}", \
    "--chat-template-content-format", "openai"]