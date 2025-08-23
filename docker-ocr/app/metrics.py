from __future__ import annotations
import time
import threading
import psutil
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

try:
    import pynvml
    pynvml.nvmlInit()
    HAS_GPU = True
except Exception:
    HAS_GPU = False

REQ_TOTAL = Counter("ocr_requests_total", "Total de requests", ["endpoint", "status"])
REQ_LAT = Histogram("ocr_request_seconds", "Latencia de requests (s)", ["endpoint"])
PAGES_TOTAL = Counter("ocr_pages_processed_total", "Páginas procesadas")
BYTES_UP = Counter("ocr_bytes_uploaded_total", "Bytes subidos")
SYS_CPU = Gauge("system_cpu_usage_percent", "CPU %")
SYS_RAM = Gauge("system_ram_usage_percent", "RAM %")
OCR_INFLIGHT = Gauge("ocr_inflight_requests", "Requests en proceso")
PAGES_ACTIVE = Gauge("ocr_pages_in_progress", "Páginas en procesamiento")
# Resumen del último documento procesado: valor = duración (s)
DOC_LAST = Gauge("ocr_last_document_seconds", "Duración del último documento (s)", ["name", "pages", "processed_at"])
if HAS_GPU:
    GPU_USED = Gauge("gpu_memory_used_bytes", "GPU mem used", ["index"])
    GPU_TOTAL = Gauge("gpu_memory_total_bytes", "GPU mem total", ["index"])
    GPU_USED_PCT = Gauge("gpu_memory_used_percent", "GPU mem %", ["index"])
else:
    GPU_USED = None
    GPU_TOTAL = None
    GPU_USED_PCT = None


def start_metrics_collector() -> None:
    t = threading.Thread(target=_loop, daemon=True)
    t.start()


def init_metric_series() -> None:
    try:
        # Inicializa series para evitar "No data" en Grafana
        for status in ("200", "400", "500"):
            REQ_TOTAL.labels(endpoint="/ocr", status=status).inc(0)
        REQ_LAT.labels(endpoint="/ocr").observe(0)
        PAGES_TOTAL.inc(0)
        BYTES_UP.inc(0)
    except Exception:
        pass


def get_metrics_latest() -> bytes:
    return generate_latest()


def get_metrics_content_type() -> str:
    return CONTENT_TYPE_LATEST


def _loop() -> None:
    while True:
        try:
            SYS_CPU.set(psutil.cpu_percent(interval=None))
            SYS_RAM.set(psutil.virtual_memory().percent)
            if HAS_GPU:
                count = pynvml.nvmlDeviceGetCount()
                for i in range(count):
                    h = pynvml.nvmlDeviceGetHandleByIndex(i)
                    m = pynvml.nvmlDeviceGetMemoryInfo(h)
                    GPU_USED.labels(index=str(i)).set(m.used)
                    GPU_TOTAL.labels(index=str(i)).set(m.total)
                    if m.total:
                        GPU_USED_PCT.labels(index=str(i)).set((m.used / m.total) * 100.0)
        except Exception:
            pass
        time.sleep(5)
