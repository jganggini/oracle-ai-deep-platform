from __future__ import annotations
from pathlib import Path
from typing import Optional, Tuple
import logging
import shutil
import subprocess
import zipfile
import re
from pypdf import PdfReader, PdfWriter
import os


def run_mineru(input_file: Path, out_dir: Path, use_gpu: bool, device: str, per_worker_vram_mb: int, backend: str, extra_args: str = "", timeout_ms: int | None = None) -> Tuple[Optional[Path], Optional[Path]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    mineru_cli = shutil.which("mineru")
    cmd = [mineru_cli or "python3", *( [] if mineru_cli else ["-m", "mineru.cli.client"] ), "-p", str(input_file), "-o", str(out_dir), "-m", "ocr", "-b", backend, "-l", "latin"]
    cmd += (["-d", device, "--vram", str(per_worker_vram_mb)] if use_gpu else ["-d", "cpu"])
    if extra_args:
        cmd += [a for a in extra_args.split(" ") if a]
    logger = logging.getLogger("mineru.cli")
    logger.info("Ejecutando MinerU: %s", " ".join(cmd))
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )

    stage_start_ts: dict[str, float] = {}
    tail_buf: list[str] = []
    try:
        from app.config import get_settings
        settings = get_settings()
        pattern_map = {
            "ocr_det": re.compile(r"OCR-det\s+latin:\s+(\d+)%"),
            "table": re.compile(r"Table\s+Predict:\s+(\d+)%"),
            "ocr_rec": re.compile(r"OCR-rec\s+Predict:\s+(\d+)%"),
            "processing_pages": re.compile(r"Processing\s+pages:\s+(\d+)%"),
        } if settings.MINERU_VERBOSE_STAGES else {}
    except Exception:
        pattern_map = {}

    assert proc.stdout is not None
    for line in proc.stdout:
        s = line.rstrip("\n")
        if not s:
            continue
        tail_buf.append(s)
        if len(tail_buf) > 50:
            tail_buf.pop(0)
        try:
            for stage, pat in pattern_map.items():
                m = pat.search(s)
                if m:
                    pct = int(m.group(1))
                    now = __import__("time").perf_counter()
                    if pct == 0 and stage not in stage_start_ts:
                        stage_start_ts[stage] = now
                        logger.info("STAGE_START %s", stage)
                    if pct in (99, 100) and stage in stage_start_ts:
                        elapsed_ms = (now - stage_start_ts[stage]) * 1000.0
                        logger.info("STAGE_END %s elapsed_ms=%.1f", stage, elapsed_ms)
                    break
        except Exception:
            pass

    ret = None
    try:
        if timeout_ms and timeout_ms > 0:
            ret = proc.wait(timeout=timeout_ms / 1000.0)
        else:
            ret = proc.wait()
    except subprocess.TimeoutExpired:
        logger = logging.getLogger("mineru.cli")
        logger.error("MinerU timeout tras %sms. Matando proceso…", timeout_ms)
        proc.kill()
        if tail_buf:
            logger.info("Salida MinerU (tail):\n%s", "\n".join(tail_buf[-80:]))
        raise RuntimeError("MinerU CLI timeout")

    if ret != 0:
        logger = logging.getLogger("mineru.cli")
        logger.error("MinerU finalizó con código %s", ret)
        if tail_buf:
            logger.info("Salida MinerU (tail):\n%s", "\n".join(tail_buf[-50:]))
        raise RuntimeError("MinerU CLI error")
    if tail_buf:
        logging.getLogger("mineru.cli").info("Salida MinerU (tail):\n%s", "\n".join(tail_buf[-50:]))

    md_path = find_or_make_md(out_dir)
    zip_candidates = list(out_dir.rglob("*.zip"))
    zip_path = next((z for z in zip_candidates if "archive" in z.name.lower() or z.name.lower().endswith(".zip")), None)
    return md_path, zip_path


def split_pdf_to_pages(pdf_path: Path, out_dir: Path) -> list[tuple[int, Path]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(str(pdf_path))
    pages: list[tuple[int, Path]] = []
    for i in range(len(reader.pages)):
        writer = PdfWriter(); writer.add_page(reader.pages[i])
        pnum = i + 1
        dst = out_dir / f"page_{pnum:04d}.pdf"
        with open(dst, "wb") as f: writer.write(f)
        pages.append((pnum, dst))
    return pages


def zip_directory(src_dir: Path, zip_path: Path) -> Path:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(src_dir):
            root_path = Path(root)
            for name in files:
                fp = root_path / name
                zf.write(fp, arcname=str(fp.relative_to(src_dir)))
    return zip_path


def annotate_single_page_markers(md_text: str, page_num: int) -> str:
    lines = md_text.splitlines()
    out: list[str] = [f"## Página {page_num} <a id=\"p{page_num}\"></a>", ""]
    paragraph: list[str] = []
    def flush() -> None:
        nonlocal paragraph
        if not paragraph: return
        joined = "\n".join(paragraph)
        out.extend(paragraph)
        if not joined.lstrip().startswith(("# ", "## ")):
            out.append(f" [p{page_num}](#p{page_num})")
        out.append("")
        paragraph = []
    for line in lines:
        if line.strip(): paragraph.append(line)
        else: flush()
    flush()
    return "\n".join(out)


def rewrite_and_copy_images(md_text: str, md_base_dir: Path, images_out_dir: Path, page_num: int) -> str:
    images_out_dir.mkdir(parents=True, exist_ok=True)
    img_re = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
    def repl(m: re.Match) -> str:
        orig = m.group(1)
        src = (md_base_dir / orig).resolve()
        if not src.exists():
            cands = list(md_base_dir.rglob(Path(orig).name))
            if cands: src = cands[0]
        if src.exists():
            dst = images_out_dir / f"p{page_num}_{Path(orig).name}"
            if not dst.exists(): dst.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(src, dst)
            return m.group(0).replace(orig, f"images/{dst.name}")
        return m.group(0)
    return img_re.sub(repl, md_text)


def find_or_make_md(out_dir: Path) -> Optional[Path]:
    preferred = [p for p in out_dir.rglob("*.md") if p.name.lower()=="upload.md" or str(p).lower().endswith("/ocr/upload.md")]
    if preferred: return max(preferred, key=lambda p: p.stat().st_mtime)
    md_files = list(out_dir.rglob("*.md"))
    if md_files: return max(md_files, key=lambda p: p.stat().st_mtime)
    txt_files = list(out_dir.rglob("*.txt"))
    if txt_files:
        t = max(txt_files, key=lambda p: p.stat().st_mtime)
        m = t.with_suffix(".md"); m.write_text(t.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8"); return m
    return None


def normalize_zip_path(s: str) -> str:
    return s.replace("\\", "/").lstrip("/")


def find_md_in_zip(zf: zipfile.ZipFile) -> Optional[str]:
    nl = zf.namelist()
    ordered = sorted(nl, key=lambda p: (0 if p.lower().endswith("/ocr/upload.md") else 1 if p.lower().endswith("/upload.md") else 2, len(p)))
    for name in ordered:
        if name.lower().endswith("upload.md"): return name
    for name in nl:
        if name.lower().endswith(".md"): return name
    return None


def build_full_from_zip(mineru_zip: Path, images_out_dir: Path) -> Optional[str]:
    try:
        with zipfile.ZipFile(mineru_zip, "r") as zf:
            md_entry = find_md_in_zip(zf)
            if not md_entry:
                return None
            raw_md = zf.read(md_entry).decode("utf-8", errors="ignore")
            md_dir = normalize_zip_path(str(Path(md_entry).parent))
            img_re = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
            nl = {n.lower(): n for n in zf.namelist()}

            def repl(m: re.Match) -> str:
                orig = m.group(1)
                rel = normalize_zip_path(orig)
                cand = f"{md_dir}/{rel}" if md_dir else rel
                entry = nl.get(cand.lower())
                if not entry:
                    base = Path(rel).name.lower()
                    entry = next((n for n in zf.namelist() if n.lower().endswith(f"/{base}") or n.lower().endswith(base)), None)
                if not entry:
                    return m.group(0)
                images_out_dir.mkdir(parents=True, exist_ok=True)
                dst = images_out_dir / Path(orig).name
                if not dst.exists():
                    with zf.open(entry, "r") as src, open(dst, "wb") as out:
                        shutil.copyfileobj(src, out)
                return m.group(0).replace(orig, f"images/{dst.name}")

            rewritten = img_re.sub(repl, raw_md)
            return rewritten
    except Exception:
        return None


def build_full_from_dir(md_path: Path, images_out_dir: Path) -> Optional[str]:
    try:
        base_dir = md_path.parent
        raw_md = md_path.read_text(encoding="utf-8", errors="ignore")
        img_re = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")

        def repl(m: re.Match) -> str:
            orig = m.group(1)
            src = (base_dir / orig).resolve()
            if not src.exists():
                cands = list(base_dir.rglob(Path(orig).name))
                if cands:
                    src = cands[0]
            if src.exists():
                images_out_dir.mkdir(parents=True, exist_ok=True)
                dst = images_out_dir / Path(orig).name
                if not dst.exists():
                    shutil.copyfile(src, dst)
                return m.group(0).replace(orig, f"images/{dst.name}")
            return m.group(0)

        return img_re.sub(repl, raw_md)
    except Exception:
        return None


def build_annotated_from_zip(mineru_zip: Path, images_out_dir: Path, page_num: int) -> Optional[str]:
    try:
        with zipfile.ZipFile(mineru_zip, "r") as zf:
            md_entry = find_md_in_zip(zf)
            if not md_entry: return None
            raw_md = zf.read(md_entry).decode("utf-8", errors="ignore")
            md_dir = normalize_zip_path(str(Path(md_entry).parent))
            img_re = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
            nl = {n.lower(): n for n in zf.namelist()}
            def repl(m: re.Match) -> str:
                orig = m.group(1)
                rel = normalize_zip_path(orig)
                cand = f"{md_dir}/{rel}" if md_dir else rel
                entry = nl.get(cand.lower())
                if not entry:
                    base = Path(rel).name.lower()
                    entry = next((n for n in zf.namelist() if n.lower().endswith(f"/{base}") or n.lower().endswith(base)), None)
                if not entry: return m.group(0)
                dst = images_out_dir / f"p{page_num}_{Path(orig).name}"
                if not dst.exists():
                    with zf.open(entry, "r") as src, open(dst, "wb") as out: shutil.copyfileobj(src, out)
                return m.group(0).replace(orig, f"images/{dst.name}")
            rewritten = img_re.sub(repl, raw_md)
            return annotate_single_page_markers(rewritten, page_num)
    except Exception:
        return None


