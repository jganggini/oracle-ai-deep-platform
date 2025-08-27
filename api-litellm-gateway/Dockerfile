FROM oraclelinux:10-slim

# Instalar Python 3 y dependencias de build mínimas (OL10-slim usa microdnf)
RUN microdnf -y install \
        python3 \
        python3-pip \
        python3-devel \
        gcc \
        make \
        openssl-devel \
        libffi-devel \
        shadow-utils \
    && microdnf clean all

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Copiar requisitos primero para mejor cacheo
COPY requirements.txt /app/requirements.txt

# Actualizar pip e instalar dependencias
RUN python3 -m pip install --upgrade pip setuptools wheel \
    && python3 -m pip install -r /app/requirements.txt

# Copiar código de la aplicación
COPY . /app

# Crear usuario opc (para alinear con key_file=/home/opc/.oci/key.pem)
RUN useradd -m -s /bin/bash opc || true

# Si existe una carpeta .oci en el contexto, copiarla a /home/opc/.oci con permisos seguros
RUN if [ -d "/app/.oci" ]; then \
        mkdir -p /home/opc/.oci && \
        cp -r /app/.oci/* /home/opc/.oci/ && \
        chown -R opc:opc /home/opc/.oci && \
        chmod -R go-rwx /home/opc/.oci && \
        find /home/opc/.oci -type f -name "*.pem" -exec chmod 600 {} \; ; \
    else \
        echo "No se encontró carpeta .oci en el contexto de build. Puedes montar -v ${PWD}/.oci:/home/opc/.oci:ro en runtime."; \
    fi

# Puerto del servicio
EXPOSE 4000

# Variables por defecto (puedes sobreescribirlas en runtime)
ENV OCI_CONFIG_FILE=/home/opc/.oci/config \
    OCI_PROFILE=ADRES

# Ejecutar como usuario opc (coincide con la ruta del key_file)
USER opc

# Comando por defecto
CMD ["python3", "start_server.py"]


