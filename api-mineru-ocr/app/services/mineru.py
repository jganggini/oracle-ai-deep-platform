from __future__ import annotations
from pathlib import Path
from typing import Optional, Tuple
import logging
import shutil
import subprocess
import zipfile
import re
import os
import json


def run_mineru(input_file: Path, out_dir: Path, use_gpu: bool, device: str, backend: str, extra_args: str = "") -> Tuple[Optional[Path], Optional[Path], list[str]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    mineru_cli = shutil.which("mineru")
    base_cmd = [
        mineru_cli or "python3",
        *( [] if mineru_cli else ["-m", "mineru.cli.client"] ),
        "-p", str(input_file),
        "-o", str(out_dir),
        "-m", "ocr",
        "-b", backend,
        "-l", "latin",
        "--make", "content_list",
        "-M", "content_list",
    ]
    if use_gpu:
        base_cmd += ["-d", device]
    else:
        base_cmd += ["-d", "cpu"]
    if extra_args:
        base_cmd += [a for a in (extra_args or "").split(" ") if a]

    def run_once(cmd: list[str]) -> tuple[int, list[str]]:
        logger_local = logging.getLogger("mineru.cli")
        logger_local.info("Ejecutando MinerU: %s", " ".join(cmd))
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
        tail: list[str] = []
        assert proc.stdout is not None
        for line in proc.stdout:
            s = line.rstrip("\n")
            if not s:
                continue
            tail.append(s)
            if len(tail) > 100:
                tail.pop(0)
        ret_code = proc.wait()
        return ret_code, tail

    # Intento único (sin fallback): la detección/reintento se gestiona en ocr.py
    ret, tail_buf = run_once(base_cmd)
    if ret != 0:
        logger = logging.getLogger("mineru.cli")
        logger.error("MinerU finalizó con código %s", ret)
        if tail_buf:
            logger.info("Salida MinerU (tail):\n%s", "\n".join(tail_buf[-50:]))
        # Propagar mensaje con tail para que la capa superior pueda decidir fallback
        tail_text = "\n".join(tail_buf[-50:]) if tail_buf else ""
        raise RuntimeError(("MinerU CLI error; tail:\n" + tail_text).strip())

    # Éxito: construir paths de salida (sin lógica de warnings aquí; se maneja en ocr.py)
    md_path = find_or_make_md(out_dir)
    zip_candidates = list(out_dir.rglob("*.zip"))
    zip_path = next((z for z in zip_candidates if "archive" in z.name.lower() or z.name.lower().endswith(".zip")), None)
    return md_path, zip_path, tail_buf


def zip_directory(src_dir: Path, zip_path: Path) -> Path:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(src_dir):
            root_path = Path(root)
            for name in files:
                fp = root_path / name
                zf.write(fp, arcname=str(fp.relative_to(src_dir)))
    return zip_path

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


def find_content_list_in_zip(zf: zipfile.ZipFile) -> Optional[str]:
    try:
        # Buscar nombres comunes de content_list
        candidates = [
            n for n in zf.namelist()
            if n.lower().endswith("content_list.json") or n.lower().endswith("content-list.json")
        ]
        if candidates:
            # priorizar rutas con "ocr/" y las más cortas
            ordered = sorted(candidates, key=lambda p: (0 if "/ocr/" in p.lower() else 1, len(p)))
            return ordered[0]
        # fallback: cualquier .json con clave de tipo content_list
        for name in zf.namelist():
            if not name.lower().endswith(".json"):
                continue
            try:
                data = json.loads(zf.read(name).decode("utf-8", errors="ignore"))
            except Exception:
                continue
            if isinstance(data, list) and data and isinstance(data[0], dict) and "page_idx" in data[0]:
                return name
    except Exception:
        return None
    return None


def build_full_from_zip(mineru_zip: Path, images_out_dir: Path) -> Tuple[Optional[str], Optional[str]]:
    try:
        with zipfile.ZipFile(mineru_zip, "r") as zf:
            # 1) Intentar usar CONTENT_LIST para construir Markdown y devolver también el JSON
            cl_entry = find_content_list_in_zip(zf)
            if cl_entry:
                try:
                    content_list_bytes = zf.read(cl_entry)
                    content_list = json.loads(content_list_bytes.decode("utf-8", errors="ignore"))
                    md = content_list_to_markdown(content_list, zf, images_out_dir, None)
                    if md:
                        return md, content_list_bytes.decode("utf-8", errors="ignore")
                except Exception:
                    pass

            # 2) Fallback a Markdown ya generado en el ZIP
            md_entry = find_md_in_zip(zf)
            if not md_entry:
                return None, None
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
            # Intentar localizar JSON por si existe también
            cl_entry2 = find_content_list_in_zip(zf)
            cl_json = zf.read(cl_entry2).decode("utf-8", errors="ignore") if cl_entry2 else None
            return rewritten, cl_json
    except Exception:
        return None, None


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


def _extract_image_from_zip(zf: zipfile.ZipFile, source_path: str, images_out_dir: Path) -> Optional[str]:
    try:
        nl = {n.lower(): n for n in zf.namelist()}
        entry = nl.get(source_path.lower())
        if not entry:
            base = Path(source_path).name.lower()
            entry = next((n for n in zf.namelist() if n.lower().endswith(f"/{base}") or n.lower().endswith(base)), None)
        if not entry:
            return None
        images_out_dir.mkdir(parents=True, exist_ok=True)
        dst = images_out_dir / Path(source_path).name
        if not dst.exists():
            with zf.open(entry, "r") as src, open(dst, "wb") as out:
                shutil.copyfileobj(src, out)
        return f"images/{dst.name}"
    except Exception:
        return None


def content_list_to_markdown(content_list: list[dict], zf: zipfile.ZipFile | None, images_out_dir: Path, content_base_dir: Path | None, add_page_markers: bool = True, add_paragraph_page_links: bool = True) -> str:
    parts: list[str] = []
    current_page: Optional[int] = None

    def append_image(img_path: str | None, captions: list[str], footnotes: list[str], page_idx_for_link: Optional[int]) -> None:
        if not img_path:
            return
        rel = normalize_zip_path(img_path)
        if zf is not None:
            new_rel = _extract_image_from_zip(zf, rel, images_out_dir)
            rel = new_rel or rel
        else:
            # Caso directorio local: resolver desde content_base_dir si se provee
            base_dir = content_base_dir or images_out_dir.parent
            src = (base_dir / rel)
            if src.exists():
                images_out_dir.mkdir(parents=True, exist_ok=True)
                dst = images_out_dir / Path(rel).name
                if not dst.exists():
                    shutil.copyfile(src, dst)
                rel = f"images/{dst.name}"
        img_md = f"![]({rel})"
        if add_paragraph_page_links and page_idx_for_link is not None:
            page_num_img = int(page_idx_for_link) + 1
            img_md = f"{img_md} [p{page_num_img}](#p{page_num_img})"
        parts.append(img_md)
        for c in captions or []:
            if c:
                parts.append(str(c))
        for f in footnotes or []:
            if f:
                parts.append(str(f))

    for item in content_list or []:
        try:
            page_idx = item.get("page_idx")
            if add_page_markers and page_idx is not None and page_idx != current_page:
                page_num = int(page_idx) + 1
                parts.append(f"## Página {page_num} <a id=\"p{page_num}\"></a>")
                parts.append("")
                current_page = page_idx

            content_type = item.get("type")
            if content_type == "text":
                text = item.get("text", "")
                text_level = item.get("text_level")
                if text_level:
                    try:
                        level = max(1, min(6, int(text_level)))
                    except Exception:
                        level = 1
                    parts.append(f"{'#' * level} {text}")
                else:
                    if text:
                        if add_paragraph_page_links and page_idx is not None:
                            page_num2 = int(page_idx) + 1
                            parts.append(f"{str(text)} [p{page_num2}](#p{page_num2})")
                        else:
                            parts.append(str(text))
            elif content_type == "image":
                append_image(item.get("img_path"), item.get("image_caption", []), item.get("image_footnote", []), page_idx)
            elif content_type == "table":
                captions = item.get("table_caption", []) or []
                footnotes = item.get("table_footnote", []) or []
                for c in captions:
                    parts.append(str(c))
                table_html = item.get("table_body", "")
                if table_html:
                    html_block = str(table_html)
                    if add_paragraph_page_links and page_idx is not None:
                        page_num_tbl = int(page_idx) + 1
                        html_block = f"{html_block}\n\n[p{page_num_tbl}](#p{page_num_tbl})"
                    parts.append(html_block)
                for f in footnotes:
                    parts.append(str(f))
            elif content_type == "equation":
                text = item.get("text", "")
                if text:
                    parts.append(f"$$\n{text}\n$$")
        except Exception:
            continue

    return "\n\n".join(parts)


def find_content_list_in_dir(base_dir: Path) -> Optional[Path]:
    try:
        candidates = [
            p for p in base_dir.rglob("*.json")
            if p.name.lower().endswith("content_list.json") or p.name.lower().endswith("content-list.json")
        ]
        if candidates:
            return sorted(candidates, key=lambda p: len(str(p)))[0]
        # Heurística: cualquier .json cuya raíz sea una lista de objetos con page_idx
        for p in base_dir.rglob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
                if isinstance(data, list) and data and isinstance(data[0], dict) and "page_idx" in data[0]:
                    return p
            except Exception:
                continue
    except Exception:
        return None
    return None

 


