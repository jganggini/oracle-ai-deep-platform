from __future__ import annotations
from fastapi import HTTPException, UploadFile, Request
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from pathlib import Path
import logging
import tempfile, os, asyncio, time, shutil, datetime
from app.config import get_settings
from app.services.metrics import BYTES_UP, OCR_INFLIGHT, DOC_LAST
from app.services.mineru import (
    run_mineru,
    build_full_from_zip,
    find_content_list_in_dir,
    content_list_to_markdown,
    zip_directory,
)


def _has_layout_bug(lines: list[str] | None) -> bool:
    if not lines:
        return False
    try:
        t = "\n".join(lines).lower()
        return (("unsupported operand type" in t and "indirectobject" in t) or ("draw_layout_bbox" in t))
    except Exception:
        return False


def _append_no_layout(extra_args: str) -> str:
    extra = (extra_args or "").strip()
    return extra if "--no-layout" in extra else (extra + " --no-layout").strip()


def _reset_out_dir(path: Path) -> None:
    try:
        if path.exists():
            shutil.rmtree(path)
    except Exception:
        pass
    path.mkdir(parents=True, exist_ok=True)


def _sanitize_pdf(original_pdf: Path) -> Path:
    """Genera una copia saneada del PDF normalizando/eliminando /Rotate."""
    from pypdf import PdfReader, PdfWriter  # type: ignore
    sane_path = original_pdf.with_name("sanitized.pdf")
    try:
        if sane_path.exists():
            sane_path.unlink()
    except Exception:
        pass
    reader = PdfReader(str(original_pdf))
    writer = PdfWriter()
    for page in reader.pages:
        try:
            rot_obj = page.get("/Rotate", 0)
            rot_int = int(rot_obj) if rot_obj is not None else 0
            page["/Rotate"] = rot_int
        except Exception:
            try:
                if "/Rotate" in page:
                    del page["/Rotate"]
            except Exception:
                pass
        writer.add_page(page)
    with open(sane_path, "wb") as f:
        writer.write(f)
    return sane_path


async def process_ocr(
    request: Request,
    file: UploadFile | None,
) -> FileResponse:
    """Procesa un PDF completo con MinerU y realiza post-procesamiento a Markdown.

    Simplificado: una sola ejecución de MinerU por documento. Se asume que el ZIP
    de salida siempre contiene CONTENT_LIST y se construye el Markdown a partir de él.
    """

    settings = get_settings()
    logger = logging.getLogger("ocr")
    t0 = time.perf_counter(); status = "200"
    try:
        OCR_INFLIGHT.inc()
        # Directorio de trabajo temporal por request
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            in_filename = "upload.pdf"
            if file is not None:  # camino multipart
                if file.filename and file.filename.lower().endswith(".pdf"):
                    # Forzar sufijo en minúsculas para compatibilidad con MinerU (evita '.PDF')
                    in_filename = Path(file.filename).with_suffix(".pdf").name
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

            # Procesamiento del documento
            out_dir = tmpdir_path / "out_doc"; out_dir.mkdir(parents=True, exist_ok=True)
            # Ejecutar MinerU; si detectamos el bug de rotación, reintentamos con --no-layout
            try:
                _md_path, mineru_zip, tail_output = await asyncio.to_thread(
                    run_mineru,
                    in_path,
                    out_dir,
                    settings.GPU_ENABLED,
                    settings.GPU_DEVICE,
                    settings.GPU_BACKEND,
                    settings.MINERU_EXTRA_ARGS,
                )
                # Si el tail trae el bug de layout, sanitizar y reintentar directamente con --no-layout
                if _has_layout_bug(tail_output):
                    logger.warning("Detectado bug de layout en tail. Sanitizando y reintentando con --no-layout.")
                    extra = _append_no_layout(settings.MINERU_EXTRA_ARGS or "")
                    sane_path = await asyncio.to_thread(_sanitize_pdf, in_path)
                    _reset_out_dir(out_dir)
                    _md_path, mineru_zip, tail_output = await asyncio.to_thread(
                        run_mineru,
                        sane_path,
                        out_dir,
                        settings.GPU_ENABLED,
                        settings.GPU_DEVICE,
                        settings.GPU_BACKEND,
                        extra,
                    )
            except Exception as e:
                err_text = str(e).lower()
                rotation_bug = (
                    ("unsupported operand type" in err_text and "indirectobject" in err_text)
                    or ("draw_layout_bbox" in err_text)
                )
                if rotation_bug:
                    logger.warning("MinerU falló por bug de layout/rotación. Sanitizando y reintentando con --no-layout. Error: %s", str(e))
                    extra = _append_no_layout(settings.MINERU_EXTRA_ARGS or "")
                    sane_path = await asyncio.to_thread(_sanitize_pdf, in_path)
                    _md_path, mineru_zip, tail_output = await asyncio.to_thread(
                        run_mineru,
                        sane_path,
                        out_dir,
                        settings.GPU_ENABLED,
                        settings.GPU_DEVICE,
                        settings.GPU_BACKEND,
                        extra,
                    )
                else:
                    logger.error("MinerU falló sin patrón conocido. Error: %s", str(e))
                    # Propagar con detalle para diagnóstico en respuesta HTTP
                    raise HTTPException(500, f"MinerU error: {str(e)}")

            # Construir Markdown y JSON priorizando el directorio local; respaldo: ZIP si existe
            final_md: str | None = None
            content_list_json: str | None = None

            # 1) Prioridad: buscar CONTENT_LIST en el directorio de salida (recursivo: incluye sanitized/ocr)
            cl_path = await asyncio.to_thread(find_content_list_in_dir, out_dir)
            if cl_path and cl_path.exists():
                try:
                    raw = await asyncio.to_thread(cl_path.read_text, "utf-8", "ignore")
                    data = __import__("json").loads(raw)
                    md_from_cl = content_list_to_markdown(data, None, images_dir, cl_path.parent)
                    if md_from_cl:
                        final_md = md_from_cl
                        content_list_json = raw
                except Exception:
                    pass

            # 2) Respaldo: usar ZIP de MinerU si existe
            if (not final_md or not content_list_json) and mineru_zip and mineru_zip.exists():
                md_zip, json_zip = await asyncio.to_thread(build_full_from_zip, mineru_zip, images_dir)
                if md_zip and json_zip:
                    final_md = md_zip
                    content_list_json = json_zip

            if not final_md or not content_list_json:
                tail_txt = "\n".join(tail_output[-50:]) if 'tail_output' in locals() and tail_output else ""
                logger.error("No se pudo construir Markdown/JSON desde salida local ni ZIP. Tail MinerU:\n%s", tail_txt)
                raise HTTPException(500, "Salida invalida: falta CONTENT_LIST o conversión fallida")

            await asyncio.to_thread((final_root / "upload.md").write_text, final_md, "utf-8")
            if content_list_json:
                await asyncio.to_thread((final_root / "content_list.json").write_text, content_list_json, "utf-8")
            # Determinar número de páginas preferentemente desde content_list.json
            pages_count: int = 0
            try:
                if content_list_json:
                    _j = __import__("json")
                    arr = _j.loads(content_list_json)
                    if isinstance(arr, list) and arr:
                        max_idx = max(int(item.get("page_idx", -1)) for item in arr if isinstance(item, dict))
                        pages_count = max(0, max_idx + 1)
            except Exception:
                pages_count = 0
            if pages_count == 0:
                try:
                    from pypdf import PdfReader  # type: ignore
                    pages_count = len(PdfReader(str(in_path)).pages)
                except Exception:
                    pages_count = 0
            # Nombrado del ZIP según nombre de entrada + páginas: <base>_P####.zip
            base_name = Path(in_filename).stem
            pages_tag = f"P{pages_count:04d}" if pages_count > 0 else "P0000"
            download_name = f"{base_name}_{pages_tag}.zip"
            src_zip = tmpdir_path / download_name; await asyncio.to_thread(zip_directory, final_root, src_zip)
            tmp_fd, tmp_zip_path = tempfile.mkstemp(suffix=".zip", prefix="mineru_ocr_"); os.close(tmp_fd); shutil.copyfile(src_zip, tmp_zip_path)
            return FileResponse(path=tmp_zip_path, media_type="application/zip", filename=download_name, background=BackgroundTask(os.remove, tmp_zip_path))
    except HTTPException as e:
        # Registrar detalle y propagar
        try:
            logger.error("HTTPException en /ocr: %s", getattr(e, "detail", str(e)))
        except Exception:
            pass
        raise
    except Exception as e:
        # Incluir motivo en la respuesta para facilitar diagnóstico
        try:
            logger.exception("Error interno en /ocr: %s", str(e))
        except Exception:
            pass
        raise HTTPException(500, f"Fallo interno: {str(e)}")
    finally:
        # Telemetría por request (para tabla en Grafana)
        try:
            duration = time.perf_counter() - t0
            processed_at = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
            # Usar páginas contadas para métricas
            name = in_filename if 'in_filename' in locals() else "upload.pdf"
            DOC_LAST.labels(
                name=name,
                pages=str(pages_count),
                processed_at=processed_at,
            ).set(duration)
        except Exception:
            pass
        # PAGES_ACTIVE eliminado en nuevo flujo
        OCR_INFLIGHT.dec()


