from fastapi import FastAPI, HTTPException, UploadFile, File, Body, Request, Form
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
import os
import logging
from typing import Optional, Tuple
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile
import re
import asyncio
from pypdf import PdfReader, PdfWriter

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MinerU OCR Service", version="2.1.0-flex")

# Configurar variables de entorno para optimización de hilos
os.environ.update({
    'OMP_NUM_THREADS': '1',
    'MKL_NUM_THREADS': '1', 
    'OPENBLAS_NUM_THREADS': '1',
    'NUMEXPR_NUM_THREADS': '1'
})


@app.get("/")
async def root():
    return {
        "service": "MinerU OCR",
        "version": "2.1.0-flex",
        "gpu_enabled": os.getenv("GPU_ENABLED", "true").lower() == "true",
        "device": os.getenv("GPU_DEVICE", "cuda"),
        "backend": os.getenv("GPU_BACKEND", "pipeline"),
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


def run_mineru(
    input_file: Path,
    out_dir: Path,
    use_gpu: bool,
    device: str,
    vram: int,
    backend: str,
) -> Tuple[Optional[Path], Optional[Path]]:
    """Ejecuta MinerU CLI"""
    out_dir.mkdir(parents=True, exist_ok=True)
    
    mineru_cli = shutil.which("mineru")
    if mineru_cli:
        cmd = [mineru_cli, "-p", str(input_file), "-o", str(out_dir)]
    else:
        cmd = ["python3", "-m", "mineru.cli.client", "-p", str(input_file), "-o", str(out_dir)]

    cmd += ["-m", "ocr", "-b", backend, "-l", "latin"]
    if use_gpu:
        cmd += ["-d", device, "--vram", str(vram)]
    else:
        cmd += ["-d", "cpu"]

    logger.info(f"[MinerU] Ejecutando: {' '.join(cmd)}")
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    if proc.returncode != 0:
        logger.error(f"[MinerU] Error: {proc.stdout}")
        raise HTTPException(status_code=500, detail="MinerU falló al procesar el documento")

    # Buscar ZIP de salida
    zip_candidates = list(out_dir.rglob("*.zip"))
    zip_path = next((z for z in zip_candidates if "archive" in z.name.lower() or z.name.lower().endswith(".zip")), None)
    
    return None, zip_path


def split_pdf_to_pages(pdf_path: Path, out_dir: Path) -> list[tuple[int, Path]]:
    """Divide PDF en páginas individuales"""
    out_dir.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(str(pdf_path))
    pages: list[tuple[int, Path]] = []
    
    for i in range(len(reader.pages)):
        writer = PdfWriter()
        writer.add_page(reader.pages[i])
        pnum = i + 1
        out_path = out_dir / f"page_{pnum:04d}.pdf"
        with open(out_path, "wb") as f:
            writer.write(f)
        pages.append((pnum, out_path))
    
    return pages


def _normalize_zip_path(path_str: str) -> str:
    return path_str.replace("\\", "/").lstrip("/")


def _find_preferred_md_entry(namelist: list[str]) -> Optional[str]:
    # Prioridad: */ocr/upload.md > */upload.md > *upload.md
    ordered = sorted(namelist, key=lambda p: (0 if p.lower().endswith("/ocr/upload.md") else 1 if p.lower().endswith("/upload.md") else 2, len(p)))
    for name in ordered:
        if name.lower().endswith("upload.md"):
            return name
    # fallback: primer .md
    for name in namelist:
        if name.lower().endswith(".md"):
            return name
    return None


def _extract_only_images_from_zip(markdown_text: str, zf: zipfile.ZipFile, md_entry_dir: str, images_out_dir: Path, page_num: int) -> str:
    images_out_dir.mkdir(parents=True, exist_ok=True)
    img_link_re = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")

    namelist = zf.namelist()
    namelist_lower = {n.lower(): n for n in namelist}

    def resolve_zip_image_path(orig_path: str) -> Optional[str]:
        # Intentar relativo al directorio del MD dentro del ZIP
        rel = _normalize_zip_path(orig_path)
        if md_entry_dir:
            cand = _normalize_zip_path(f"{md_entry_dir}/{rel}")
            if cand.lower() in namelist_lower:
                return namelist_lower[cand.lower()]
        # Buscar por basename
        base = Path(rel).name.lower()
        for n in namelist:
            if n.lower().endswith(f"/{base}") or n.lower().endswith(base):
                return n
        return None

    def replace_match(m: re.Match) -> str:
        orig_path = m.group(1)
        try:
            entry = resolve_zip_image_path(orig_path)
            if entry is None:
                return m.group(0)
            dst_name = f"p{page_num}_" + Path(orig_path).name
            dst = images_out_dir / dst_name
            if not dst.exists():
                with zf.open(entry, "r") as src, open(dst, "wb") as out:
                    shutil.copyfileobj(src, out)
            new_path = f"images/{dst_name}"
            return m.group(0).replace(orig_path, new_path)
        except Exception:
            return m.group(0)

    return img_link_re.sub(replace_match, markdown_text)


def build_annotated_from_zip(mineru_zip: Path, images_out_dir: Path, page_num: int) -> Optional[str]:
    try:
        with zipfile.ZipFile(mineru_zip, "r") as zf:
            namelist = zf.namelist()
            md_entry = _find_preferred_md_entry(namelist)
            if not md_entry:
                return None
            raw_md = zf.read(md_entry).decode("utf-8", errors="ignore")
            md_entry_dir = _normalize_zip_path(str(Path(md_entry).parent))
            rewritten = _extract_only_images_from_zip(raw_md, zf, md_entry_dir, images_out_dir, page_num)
            annotated = annotate_single_page_markers(rewritten, page_num)
            return annotated
    except Exception:
        return None


def find_or_make_md(out_dir: Path) -> Optional[Path]:
    """Busca o genera Markdown desde la salida de MinerU"""
    # Buscar upload.md en rutas conocidas
    preferred_paths = [
        out_dir / "upload.md",
        out_dir / "ocr" / "upload.md",
        *list(out_dir.rglob("*/ocr/upload.md"))
    ]
    
    for path in preferred_paths:
        if path.exists():
            return path
    
    # Fallback: buscar cualquier .md
    md_files = list(out_dir.rglob("*.md"))
    if md_files:
        return max(md_files, key=lambda p: p.stat().st_mtime)
    
    # Fallback: convertir .txt a .md
    txt_files = list(out_dir.rglob("*.txt"))
    if txt_files:
        txt_path = max(txt_files, key=lambda p: p.stat().st_mtime)
        md_path = txt_path.with_suffix(".md")
        try:
            content = txt_path.read_text(encoding="utf-8", errors="ignore")
            md_path.write_text(content, encoding="utf-8")
            return md_path
        except Exception:
            pass
    
    return None


def annotate_single_page_markers(md_text: str, page_num: int) -> str:
    """Anota Markdown con encabezado de página y marcadores por párrafo"""
    lines = md_text.splitlines()
    out_lines = [f"## Página {page_num} <a id=\"p{page_num}\"></a>", ""]
    
    paragraph: list[str] = []
    
    def flush_paragraph() -> None:
        nonlocal paragraph
        if not paragraph:
            return
        joined = "\n".join(paragraph)
        if joined.lstrip().startswith("# ") or joined.lstrip().startswith("## "):
            out_lines.extend(paragraph)
        else:
            out_lines.extend(paragraph)
            out_lines.append(f" [p{page_num}](#p{page_num})")
        out_lines.append("")
        paragraph = []
    
    for line in lines:
        if line.strip() == "":
            flush_paragraph()
        else:
            paragraph.append(line)
    
    flush_paragraph()
    return "\n".join(out_lines)


def rewrite_and_copy_images(md_text: str, md_base_dir: Path, images_out_dir: Path, page_num: int) -> str:
    """Reescribe rutas de imágenes y las copia a images/"""
    images_out_dir.mkdir(parents=True, exist_ok=True)
    img_link_re = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")

    def replace_match(m: re.Match) -> str:
        orig_path = m.group(1)
        try:
            src = (md_base_dir / orig_path).resolve()
            if not src.exists():
                # Buscar imagen en subdirectorios
                alt = list(md_base_dir.rglob(Path(orig_path).name))
                src = alt[0] if alt else src
            
            if src.exists():
                dst_name = f"p{page_num}_{Path(orig_path).name}"
                dst = images_out_dir / dst_name
                if not dst.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src, dst)
                new_path = f"images/{dst_name}"
                return m.group(0).replace(orig_path, new_path)
        except Exception:
            pass
        return m.group(0)

    return img_link_re.sub(replace_match, md_text)


def zip_directory(src_dir: Path, zip_path: Path) -> Path:
    """Comprime directorio a ZIP"""
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(src_dir):
            root_path = Path(root)
            for name in files:
                fp = root_path / name
                arc = fp.relative_to(src_dir)
                zf.write(fp, arcname=str(arc))
    return zip_path


def process_page(
    pnum: int, 
    page_pdf: Path, 
    tmpdir_path: Path,
    use_gpu: bool,
    device: str,
    vram_limit: int,
    backend: str,
    final_pages_dir: Path,
    images_out_dir: Path
) -> tuple[int, Optional[str]]:
    """Procesa una página individual con MinerU"""
    page_out_dir = tmpdir_path / "pages_out" / f"p{pnum:04d}"
    page_out_dir.mkdir(parents=True, exist_ok=True)
    
    _md, mineru_zip = run_mineru(page_pdf, page_out_dir, use_gpu, device, vram_limit, backend)

    annotated: Optional[str] = None
    if mineru_zip and mineru_zip.exists():
        # Optimización: leer solo upload.md e imágenes referenciadas desde el ZIP
        annotated = build_annotated_from_zip(mineru_zip, images_out_dir, pnum)
    if annotated is None:
        # Fallback: extraer a disco y proceder como antes
        work_dir = page_out_dir
        if mineru_zip and mineru_zip.exists():
            work_dir = tmpdir_path / "zip_pages" / f"p{pnum:04d}"
            work_dir.mkdir(parents=True, exist_ok=True)
            try:
                with zipfile.ZipFile(mineru_zip, "r") as zf:
                    zf.extractall(path=work_dir)
            except Exception:
                pass
        md_in_page = find_or_make_md(work_dir)
        if not md_in_page or not md_in_page.exists():
            return (pnum, None)
        try:
            raw_text = md_in_page.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            raw_text = ""
        rewritten = rewrite_and_copy_images(raw_text, md_in_page.parent, images_out_dir, pnum)
        annotated = annotate_single_page_markers(rewritten, pnum)
    
    # Guardar ZIP por página
    page_zip_dst = final_pages_dir / f"page_{pnum:04d}.zip"
    try:
        if mineru_zip and mineru_zip.exists():
            shutil.copyfile(mineru_zip, page_zip_dst)
        else:
            tmp_zip = tmpdir_path / f"p{pnum:04d}.zip"
            zip_directory(page_out_dir, tmp_zip)
            shutil.copyfile(tmp_zip, page_zip_dst)
    except Exception:
        pass
    
    return (pnum, annotated)


async def process_page_async(
    pnum: int, 
    page_pdf: Path, 
    tmpdir_path: Path,
    use_gpu: bool,
    device: str,
    vram_limit: int,
    backend: str,
    final_pages_dir: Path,
    images_out_dir: Path
) -> tuple[int, Optional[str]]:
    """Wrapper async para process_page que ejecuta en thread separado"""
    return await asyncio.to_thread(
        process_page,
        pnum, page_pdf, tmpdir_path, use_gpu, device, vram_limit, backend,
        final_pages_dir, images_out_dir
    )


@app.post("/ocr")
async def ocr_endpoint(
    request: Request,
    file: UploadFile | None = File(None),
    raw: bytes | None = Body(None),
    # Parámetros por request (solo Form)
    vram_limit: int = Form(..., ge=256),
    concurrency: int = Form(..., ge=1),
    use_gpu: bool = Form(True),
    device: str = Form("cuda"),
    backend: str = Form("pipeline"),
):
    """Endpoint OCR con parámetros por request (Form-only: vram_limit, concurrency)"""
    try:
        # Forzar GPU off si el entorno lo deshabilita
        if os.getenv("GPU_ENABLED", "true").lower() != "true":
            use_gpu = False

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Preparar archivo de entrada
            in_filename = "upload.pdf"
            if file is not None:
                if file.filename and file.filename.lower().endswith(".pdf"):
                    in_filename = Path(file.filename).name
                in_path = tmpdir_path / in_filename
                with open(in_path, "wb") as fout:
                    while True:
                        chunk = await file.read(1024 * 1024)
                        if not chunk:
                            break
                        fout.write(chunk)
            else:
                data_bytes = raw if raw is not None else await request.body()
                if not data_bytes:
                    raise HTTPException(status_code=400, detail="No se recibió archivo")
                in_path = tmpdir_path / in_filename
                in_path.write_bytes(data_bytes)
            
            # Dividir PDF en páginas
            pages_src_dir = tmpdir_path / "pages_src"
            pages = split_pdf_to_pages(in_path, pages_src_dir)
            if not pages:
                raise HTTPException(status_code=500, detail="No se pudieron generar páginas del PDF")
            
            # Preparar directorios de salida
            final_root = tmpdir_path / "final"
            final_pages_dir = final_root / "pages"
            images_out_dir = final_root / "images"
            final_root.mkdir(parents=True, exist_ok=True)
            final_pages_dir.mkdir(parents=True, exist_ok=True)
            
            # Calcular concurrencia efectiva por VRAM
            try:
                per_worker = int(os.getenv("MINERU_VRAM_PER_WORKER_MB", "768"))
                if per_worker < 256:
                    per_worker = 256
            except Exception:
                per_worker = 768
            allowed_by_vram = (vram_limit // per_worker) if use_gpu else concurrency
            if allowed_by_vram < 1:
                raise HTTPException(status_code=400, detail=f"VRAM insuficiente para al menos 1 worker (per_worker={per_worker}MB)")
            max_workers = max(1, min(concurrency, allowed_by_vram))
            
            sem = asyncio.Semaphore(max_workers)
            
            async def process_with_semaphore(pnum: int, page_pdf: Path) -> tuple[int, Optional[str]]:
                async with sem:
                    return await process_page_async(
                        pnum, page_pdf, tmpdir_path, use_gpu, device, vram_limit, backend,
                        final_pages_dir, images_out_dir
                    )
            
            # Procesar páginas en paralelo
            tasks = [process_with_semaphore(pnum, page_pdf) for pnum, page_pdf in pages]
            results = await asyncio.gather(*tasks)
            
            # Consolidar resultados
            combined_parts: list[str] = []
            for pnum, annotated in sorted(results, key=lambda x: x[0]):
                if annotated:
                    combined_parts.append(annotated)
            
            # Escribir upload.md consolidado
            combined_md_path = final_root / "upload.md"
            combined_md_path.write_text("\n\n".join(combined_parts), encoding="utf-8")
            
            # Empaquetar como ZIP
            src_zip = tmpdir_path / "upload.zip"
            zip_directory(final_root, src_zip)
            
            # Copiar a archivo temporal persistente
            tmp_fd, tmp_zip_path = tempfile.mkstemp(suffix=".zip", prefix="mineru_ocr_")
            os.close(tmp_fd)
            shutil.copyfile(src_zip, tmp_zip_path)
            
            return FileResponse(
                path=tmp_zip_path,
                media_type="application/zip",
                filename="upload.zip",
                background=BackgroundTask(os.remove, tmp_zip_path),
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("OCR error")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("MINERU_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)


