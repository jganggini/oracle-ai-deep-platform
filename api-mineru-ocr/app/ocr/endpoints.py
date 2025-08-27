from __future__ import annotations
from fastapi import APIRouter, HTTPException, UploadFile, File, Body, Form, Request
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from pathlib import Path
import tempfile, os, asyncio, time, shutil, datetime
from ..config import get_settings
from app.metrics import BYTES_UP, OCR_INFLIGHT, PAGES_ACTIVE, DOC_LAST
from .mineru_runner import (
    run_mineru,
    split_pdf_to_pages,
    find_or_make_md,
    rewrite_and_copy_images,
    annotate_single_page_markers,
    build_annotated_from_zip,
    zip_directory,
)

router = APIRouter()


@router.post("/ocr")
async def ocr_endpoint(
    request: Request,
    file: UploadFile | None = File(None),  # PDF vía multipart (opcional)
    raw: bytes | None = Body(None),        # PDF en bytes crudos (alternativa)
    vram_limit: int = Form(..., ge=256),   # VRAM total asignada (MB)
    concurrency: int = Form(..., ge=1),    # procesos paralelos solicitados
    per_worker_mb: int | None = Form(None, ge=256),  # opcional: VRAM por worker (MB)
):
    """Procesa un PDF página a página usando MinerU con control de concurrencia.

    Pasos:
    1) Recibe archivo (multipart) o bytes crudos y los guarda temporalmente
    2) Divide el PDF en páginas individuales
    3) Ejecuta MinerU por página con semáforo de concurrencia limitado por VRAM
    4) Reconstruye un ZIP con upload.md e imágenes reescritas
    5) Actualiza métricas y devuelve el ZIP resultante
    """

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
            else:  # camino raw bytes en body
                data_bytes = raw if raw is not None else await request.body()
                if not data_bytes:
                    status = "400"; raise HTTPException(400, "No se recibió archivo")
                in_path = tmpdir_path / in_filename
                in_path.write_bytes(data_bytes); BYTES_UP.inc(len(data_bytes))

            pages_src_dir = tmpdir_path / "pages_src"
            pages = split_pdf_to_pages(in_path, pages_src_dir)
            if not pages:
                status = "500"; raise HTTPException(500, "No se pudieron generar páginas del PDF")
            PAGES_ACTIVE.set(len(pages))  # gauge de progreso

            final_root = tmpdir_path / "final"; final_pages = final_root / "pages"; images_dir = final_root / "images"
            final_root.mkdir(parents=True, exist_ok=True); final_pages.mkdir(parents=True, exist_ok=True)

            per_worker = per_worker_mb if per_worker_mb is not None else settings.MINERU_VRAM_PER_WORKER_MB
            allowed_by_vram = (vram_limit // per_worker) if settings.GPU_ENABLED else concurrency
            if allowed_by_vram < 1:
                status = "400"; raise HTTPException(400, f"VRAM insuficiente para 1 worker (per_worker={per_worker}MB)")
            max_workers = max(1, min(concurrency, allowed_by_vram))
            sem = asyncio.Semaphore(max_workers)

            async def process_one(pnum: int, pdf: Path):
                async with sem:
                    out_dir = tmpdir_path / "pages_out" / f"p{pnum:04d}"; out_dir.mkdir(parents=True, exist_ok=True)
                    _md, mineru_zip = await asyncio.to_thread(run_mineru, pdf, out_dir, settings.GPU_ENABLED, settings.GPU_DEVICE, vram_limit, settings.GPU_BACKEND)
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
                    return (pnum, annotated)

            # Ejecuta tareas de páginas respetando el semáforo
            results = await asyncio.gather(*[process_one(p, pdf) for p, pdf in pages])
            parts: list[str] = []
            for pnum, md in sorted(results, key=lambda x: x[0]):
                if md: parts.append(md)
            await asyncio.to_thread((final_root / "upload.md").write_text, "\n\n".join(parts), "utf-8")
            src_zip = tmpdir_path / "upload.zip"; await asyncio.to_thread(zip_directory, final_root, src_zip)
            tmp_fd, tmp_zip_path = tempfile.mkstemp(suffix=".zip", prefix="mineru_ocr_"); os.close(tmp_fd); shutil.copyfile(src_zip, tmp_zip_path)
            return FileResponse(path=tmp_zip_path, media_type="application/zip", filename="upload.zip", background=BackgroundTask(os.remove, tmp_zip_path))
    except HTTPException as e:
        status = str(e.status_code); raise
    except Exception:
        status = "500"; raise
    finally:
        # Telemetría por request (para tabla en Grafana)
        duration = time.perf_counter() - t0
        processed_at = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
        pages_count = len(pages) if 'pages' in locals() else 0
        name = in_filename if 'in_filename' in locals() else "upload.pdf"
        try:
            DOC_LAST.labels(
                name=name,
                pages=str(pages_count),
                processed_at=processed_at,
                vram=str(vram_limit),
                concurrency=str(concurrency),
            ).set(duration)
        except Exception:
            pass
        PAGES_ACTIVE.set(0)
        OCR_INFLIGHT.dec()
