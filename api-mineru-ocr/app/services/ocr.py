from __future__ import annotations
from fastapi import HTTPException, UploadFile, Request
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from pathlib import Path
import tempfile, os, asyncio, time, shutil, datetime
from app.config import get_settings
from app.services.metrics import BYTES_UP, OCR_INFLIGHT, PAGES_ACTIVE, DOC_LAST
from app.services.mineru import (
    run_mineru,
    split_pdf_to_pages,
    find_or_make_md,
    rewrite_and_copy_images,
    annotate_single_page_markers,
    build_annotated_from_zip,
    zip_directory,
)


async def process_ocr(
    request: Request,
    file: UploadFile | None,
    per_worker_mb: int | None,
    workers_cap: int | None,
) -> FileResponse:
    """Procesa un PDF página a página usando MinerU con control de concurrencia."""

    settings = get_settings()
    t0 = time.perf_counter(); status = "200"
    try:
        OCR_INFLIGHT.inc()
        # Directorio de trabajo temporal por request
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            in_filename = "upload.pdf"
            if file is not None:  # camino multipart
                if file.filename and file.filename.lower().endswith(".pdf"):
                    in_filename = Path(file.filename).name
                in_path = tmpdir_path / in_filename
                total = 0
                with open(in_path, "wb") as fout:
                    while True:
                        chunk = await file.read(1024 * 1024)
                        if not chunk: break
                        total += len(chunk); fout.write(chunk)
                BYTES_UP.inc(total)
            else:
                status = "400"; raise HTTPException(400, "No se recibió archivo")

            # Rutas finales
            final_root = tmpdir_path / "final"; final_pages = final_root / "pages"; images_dir = final_root / "images"
            final_root.mkdir(parents=True, exist_ok=True); final_pages.mkdir(parents=True, exist_ok=True)

            # Parámetros de concurrencia
            per_worker = per_worker_mb if per_worker_mb is not None else settings.MINERU_VRAM_PER_WORKER_MB
            # Detectar VRAM total
            total_vram_mb = 0
            if settings.GPU_ENABLED:
                try:
                    import pynvml  # type: ignore
                    pynvml.nvmlInit()
                    count = pynvml.nvmlDeviceGetCount()
                    for i in range(count):
                        h = pynvml.nvmlDeviceGetHandleByIndex(i)
                        m = pynvml.nvmlDeviceGetMemoryInfo(h)
                        total_vram_mb += int(m.total // (1024 * 1024))
                except Exception:
                    total_vram_mb = per_worker
            # Limitar por CPU
            import os as _os
            cpu_cores = max(1, _os.cpu_count() or 1)
            # Considerar overhead de VRAM por proceso
            overhead_mb = getattr(settings, "MINERU_VRAM_OVERHEAD_MB", 0) or 0
            vram_per_proc = max(1, per_worker + overhead_mb)
            allowed_by_vram = (total_vram_mb // vram_per_proc) if settings.GPU_ENABLED else 1
            max_workers = max(1, min(allowed_by_vram, cpu_cores))
            # Cap opcional: prioriza parámetro de la API; si no, usa settings
            cap_value = workers_cap if (workers_cap is not None) else getattr(settings, "MINERU_WORKERS_CAP", None)
            if cap_value:
                try:
                    max_workers = min(max_workers, int(cap_value))
                except Exception:
                    pass
            if allowed_by_vram < 1:
                status = "400"; raise HTTPException(400, f"VRAM insuficiente para 1 worker (per_worker={per_worker}MB)")

            # Segmentación por páginas
            pages_src_dir = tmpdir_path / "pages_src"
            pages = split_pdf_to_pages(in_path, pages_src_dir)
            if not pages:
                status = "500"; raise HTTPException(500, "No se pudieron generar páginas del PDF")
            PAGES_ACTIVE.set(len(pages))

            sem = asyncio.Semaphore(max_workers)

            pages_done = 0

            async def process_one(pnum: int, pdf: Path, queued_t0: float):
                t_acquire_start = time.perf_counter()
                async with sem:
                    out_dir = tmpdir_path / "pages_out" / f"p{pnum:04d}"; out_dir.mkdir(parents=True, exist_ok=True)

                    t1 = time.perf_counter()
                    _md, mineru_zip = await asyncio.to_thread(
                        run_mineru,
                        pdf,
                        out_dir,
                        settings.GPU_ENABLED,
                        settings.GPU_DEVICE,
                        per_worker,
                        settings.GPU_BACKEND,
                        settings.MINERU_EXTRA_ARGS,
                        settings.MINERU_PAGE_TIMEOUT_MS,
                    )
                    t2 = time.perf_counter()

                    annotated = await asyncio.to_thread(build_annotated_from_zip, mineru_zip, images_dir, pnum) if mineru_zip else None
                    if annotated is None:
                        work_dir = out_dir
                        if mineru_zip:
                            import zipfile
                            work_dir = tmpdir_path / "zip_pages" / f"p{pnum:04d}"; work_dir.mkdir(parents=True, exist_ok=True)
                            await asyncio.to_thread(lambda: zipfile.ZipFile(mineru_zip, "r").extractall(path=work_dir))
                        md = await asyncio.to_thread(find_or_make_md, work_dir)
                        if md:
                            raw_md = await asyncio.to_thread(md.read_text, "utf-8", "ignore")
                            rewritten = await asyncio.to_thread(rewrite_and_copy_images, raw_md, md.parent, images_dir, pnum)
                            annotated = await asyncio.to_thread(annotate_single_page_markers, rewritten, pnum)

                    if annotated is None: annotated = ""

                    # Telemetría simple por página
                    try:
                        import psutil  # type: ignore
                        _ = psutil.cpu_percent(interval=None)
                    except Exception:
                        pass

                    nonlocal pages_done
                    pages_done += 1
                    return (pnum, annotated)

            # Ejecuta páginas con concurrencia (ramp-up opcional)
            delay_ms = getattr(settings, "MINERU_RAMP_DELAY_MS", 0) or 0
            async def delayed_start(i: int, pnum: int, pdf_path: Path):
                if delay_ms > 0:
                    await asyncio.sleep((i * delay_ms) / 1000.0)
                return await process_one(pnum, pdf_path, time.perf_counter())

            tasks = [asyncio.create_task(delayed_start(i, p, pdf)) for i, (p, pdf) in enumerate(pages)]
            results_raw = await asyncio.gather(*tasks, return_exceptions=True)

            # Filtrar y registrar errores por página
            results: list[tuple[int, str]] = []
            for idx, item in enumerate(results_raw):
                if isinstance(item, Exception):
                    continue
                if item is None:
                    continue
                results.append(item)
            parts: list[str] = []
            for pnum, md in sorted(results, key=lambda x: x[0]):
                if md: parts.append(md)
            merged_md = "\n\n".join(parts)

            await asyncio.to_thread((final_root / "upload.md").write_text, merged_md, "utf-8")
            src_zip = tmpdir_path / "upload.zip"; await asyncio.to_thread(zip_directory, final_root, src_zip)
            tmp_fd, tmp_zip_path = tempfile.mkstemp(suffix=".zip", prefix="mineru_ocr_"); os.close(tmp_fd); shutil.copyfile(src_zip, tmp_zip_path)
            return FileResponse(path=tmp_zip_path, media_type="application/zip", filename="upload.zip", background=BackgroundTask(os.remove, tmp_zip_path))
    except HTTPException:
        raise
    except Exception:
        raise
    finally:
        # Telemetría por request (para tabla en Grafana)
        try:
            duration = time.perf_counter() - t0
            processed_at = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
            pages_count = len(pages) if 'pages' in locals() else 0
            name = in_filename if 'in_filename' in locals() else "upload.pdf"
            DOC_LAST.labels(
                name=name,
                pages=str(pages_count),
                processed_at=processed_at,
                vram=str(total_vram_mb if 'total_vram_mb' in locals() else 0),
                concurrency=str(sem._value if 'sem' in locals() else 1),
            ).set(duration)
        except Exception:
            pass
        PAGES_ACTIVE.set(0)
        OCR_INFLIGHT.dec()


