from __future__ import annotations
import time
import threading
import psutil
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST

try:
    import pynvml  # type: ignore
    _NVML_AVAILABLE = True
except Exception:
    pynvml = None  # type: ignore
    _NVML_AVAILABLE = False

# Sistema
SYS_CPU = Gauge("system_cpu_usage_percent", "CPU %")
SYS_RAM = Gauge("system_ram_usage_percent", "RAM %")

# GPU (por índice)
GPU_USED = Gauge("gpu_memory_used_bytes", "GPU mem used (bytes)", ["index"])
GPU_TOTAL = Gauge("gpu_memory_total_bytes", "GPU mem total (bytes)", ["index"])
GPU_USED_PCT = Gauge("gpu_memory_used_percent", "GPU mem usada %", ["index"])

# OCR flujo (a nivel de documento)
OCR_INFLIGHT = Gauge("ocr_inflight_requests", "Requests en proceso")
BYTES_UP = Counter("ocr_bytes_uploaded_total", "Bytes subidos")

# Último documento procesado
DOC_LAST = Gauge(
    "ocr_last_document_seconds",
    "Duración del último documento (s)",
    ["name", "pages", "processed_at"],
)


def start_metrics_collector() -> None:
    t = threading.Thread(target=_loop, daemon=True)
    t.start()


def init_metric_series() -> None:
    BYTES_UP.inc(0)
    OCR_INFLIGHT.set(0)

    if _NVML_AVAILABLE:
        try:
            pynvml.nvmlInit()
            count = pynvml.nvmlDeviceGetCount()
            for i in range(count):
                idx = str(i)
                h = pynvml.nvmlDeviceGetHandleByIndex(i)
                m = pynvml.nvmlDeviceGetMemoryInfo(h)
                GPU_USED.labels(index=idx).set(0)
                GPU_TOTAL.labels(index=idx).set(m.total)
                GPU_USED_PCT.labels(index=idx).set(0)
        except Exception:
            pass


def get_metrics_latest() -> bytes:
    return generate_latest()


def get_metrics_content_type() -> str:
    return CONTENT_TYPE_LATEST


def _loop() -> None:
    while True:
        cpu_pct = psutil.cpu_percent(interval=None)
        ram_pct = psutil.virtual_memory().percent
        SYS_CPU.set(cpu_pct)
        SYS_RAM.set(ram_pct)

        if _NVML_AVAILABLE:
            try:
                try:
                    pynvml.nvmlInit()
                except Exception:
                    pass
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
            except Exception:
                pass

        time.sleep(5)


