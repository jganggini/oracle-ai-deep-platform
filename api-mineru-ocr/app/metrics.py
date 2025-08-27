from __future__ import annotations
import time
import threading
import psutil
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Asumimos GPU siempre disponible (simplifica la lógica y evita ramas muertas)
import pynvml  # type: ignore
pynvml.nvmlInit()

# =============================
# Métricas expuestas (Grafana)
# =============================

# Sistema
SYS_CPU = Gauge("system_cpu_usage_percent", "CPU %")
SYS_RAM = Gauge("system_ram_usage_percent", "RAM %")

# GPU (por índice)
GPU_USED = Gauge("gpu_memory_used_bytes", "GPU mem used (bytes)", ["index"])
GPU_TOTAL = Gauge("gpu_memory_total_bytes", "GPU mem total (bytes)", ["index"])
GPU_USED_PCT = Gauge("gpu_memory_used_percent", "GPU mem usada %", ["index"])

# OCR flujo
OCR_INFLIGHT = Gauge("ocr_inflight_requests", "Requests en proceso")
PAGES_ACTIVE = Gauge("ocr_pages_in_progress", "Páginas en procesamiento")
BYTES_UP = Counter("ocr_bytes_uploaded_total", "Bytes subidos")

# Último documento procesado (valor = duración en segundos)
DOC_LAST = Gauge(
    "ocr_last_document_seconds",
    "Duración del último documento (s)",
    ["name", "pages", "processed_at", "vram", "concurrency"],
)


def start_metrics_collector() -> None:
    t = threading.Thread(target=_loop, daemon=True)
    t.start()


def init_metric_series() -> None:
    # Inicializa series para evitar "No data" en Grafana
    BYTES_UP.inc(0)
    OCR_INFLIGHT.set(0)
    PAGES_ACTIVE.set(0)

    # Inicializa métricas por GPU
    count = pynvml.nvmlDeviceGetCount()
    for i in range(count):
        idx = str(i)
        h = pynvml.nvmlDeviceGetHandleByIndex(i)
        m = pynvml.nvmlDeviceGetMemoryInfo(h)
        GPU_USED.labels(index=idx).set(0)
        GPU_TOTAL.labels(index=idx).set(m.total)
        GPU_USED_PCT.labels(index=idx).set(0)


def get_metrics_latest() -> bytes:
    return generate_latest()


def get_metrics_content_type() -> str:
    return CONTENT_TYPE_LATEST


def _loop() -> None:
    while True:
        # CPU / RAM
        cpu_pct = psutil.cpu_percent(interval=None)
        ram_pct = psutil.virtual_memory().percent
        SYS_CPU.set(cpu_pct)
        SYS_RAM.set(ram_pct)

        # GPU por índice – porcentaje preciso usado/total
        count = pynvml.nvmlDeviceGetCount()
        for i in range(count):
            idx = str(i)
            h = pynvml.nvmlDeviceGetHandleByIndex(i)
            m = pynvml.nvmlDeviceGetMemoryInfo(h)
            used = float(m.used)
            total = float(m.total) if m.total else 0.0
            GPU_USED.labels(index=idx).set(used)
            GPU_TOTAL.labels(index=idx).set(total)
            GPU_USED_PCT.labels(index=idx).set((used / total) * 100.0 if total > 0 else 0.0)

        time.sleep(5)
