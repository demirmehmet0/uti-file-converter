
import os
import uuid
import shutil
import hashlib
import tempfile
import urllib.request
import subprocess

from PIL import Image as PILImage

OUTPUT_DIR = "/storage/FileConverter/"

# Dropdown values arrive either as a plain extension ("png") or as a MIME type
# ("image/jpeg"). Normalise everything to a canonical extension.
MIME_TO_EXT = {
    "application/pdf": "pdf",
    "image/jpeg": "jpg",
    "image/pwg-raster": "pwg",
    "image/urf": "urf",
    "application/vnd.hp-pcl": "pcl",
    "application/pcl": "pcl",
    "application/postscript": "ps",
    "application/vnd.hp-pclxl": "pclxl",
    "application/octet-stream": "bin",
    # already-extension values map to themselves
    "pdf": "pdf",
    "docx": "docx",
    "txt": "txt",
    "png": "png",
    "jpg": "jpg",
    "webp": "webp",
}

EXT_TO_MIME = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain",
    "png": "image/png",
    "jpg": "image/jpeg",
    "webp": "image/webp",
    "ps": "application/postscript",
    "pcl": "application/vnd.hp-pcl",
    "pclxl": "application/vnd.hp-pclxl",
    "pwg": "image/pwg-raster",
    "urf": "image/urf",
    "bin": "application/octet-stream",
}

IMAGE_EXTS = {"png", "jpg", "jpeg", "webp", "bmp", "tiff", "gif"}
DOCUMENT_EXTS = {"pdf", "docx", "txt", "odt", "rtf", "html"}
PRINTER_EXTS = {"ps", "pcl", "pclxl", "pwg", "urf"}


def download_from_storage(storageID):
    """Resolve a storage entry to a local /storage path, downloading if needed.

    Mirrors VideoFeed's storage handling: re-download only when the file is
    missing or its MD5 no longer matches the stored hash.
    """
    # Imported lazily so the conversion helpers can be used/tested without the SDK.
    from sdks.novavision.src.helper.package import PackageHelper

    result = PackageHelper.get_storage_details(storageID)
    data = result["data"]
    url_path = result["data_url"]
    file_path = f"/storage/{data['name']}"

    if os.path.exists(file_path):
        if md5_hash(file_path) != data["hash_file"]:
            urllib.request.urlretrieve(url_path, file_path)
    else:
        urllib.request.urlretrieve(url_path, file_path)

    return file_path


def resolve_source_path(input_file):
    """Extract the source file path from a (possibly list/dict/File) input value."""
    if input_file is None:
        return None
    if isinstance(input_file, list):
        input_file = input_file[0] if input_file else None
    if isinstance(input_file, dict):
        return input_file.get("path")
    return getattr(input_file, "path", None)


def materialize_source_path(input_file, redis_db):
    """Return a real on-disk path for the conversion tools to read.

    Files now travel as Redis-backed BinaryFile references (no /storage path),
    so the bytes are pulled from Redis and written to a temp file. A legacy
    input that still carries a valid `path` is used as-is for back-compat.
    """
    from sdks.novavision.src.media.file import BinaryFile

    if input_file is None:
        return None

    legacy_path = resolve_source_path(input_file)
    if legacy_path and os.path.exists(legacy_path):
        return legacy_path

    binary = BinaryFile.get_frame(input_file, redis_db)
    if binary is None or not binary.value:
        return None

    ext = os.path.splitext(binary.name)[1] or ".bin"
    tmp_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4().hex}{ext}")
    with open(tmp_path, "wb") as f:
        f.write(binary.value)

    return tmp_path


def _param(request, name, default=None):
    """Safely read a request param; return default if absent or on error."""
    try:
        value = request.get_param(name)
    except Exception:
        return default
    return default if value is None else value


def build_options(request, target_value):
    """Collect the format-specific parameters relevant to target_value.

    Only the params that belong to the chosen format are queried, so formats
    without extra settings (txt, docx, pdf, ps) yield an empty dict.
    """
    target_ext = MIME_TO_EXT.get(target_value, target_value)
    options = {}

    if target_ext in ("jpg", "jpeg", "webp"):
        options["quality"] = int(_param(request, "ConfigQuality", 90))
    elif target_ext == "png":
        options["compression"] = int(_param(request, "ConfigCompression", 6))
    elif target_ext in PRINTER_EXTS and target_ext != "ps":
        options["dpi"] = int(_param(request, "ConfigResolution", 300))
        options["page_size"] = _param(request, "ConfigPageSize", "A4")
        options["color_space"] = int(_param(request, "ConfigColorSpace", 19))
        options["duplex"] = int(_param(request, "ConfigDuplex", 0))
        options["media_position"] = int(_param(request, "ConfigMediaPosition", 0))
        options["media_type"] = int(_param(request, "ConfigMediaType", 0))

    return options


def _convert_image_to_document(source_path, target_ext, out_path):
    """Image → document via a PDF intermediate (Pillow → LibreOffice)."""
    tmp_pdf = _ensure_pdf(source_path)
    try:
        if target_ext == "pdf":
            shutil.copyfile(tmp_pdf, out_path)
        else:
            _convert_document(tmp_pdf, target_ext, out_path)
    finally:
        if tmp_pdf != source_path and os.path.exists(tmp_pdf):
            os.remove(tmp_pdf)


def convert_file(source_path, target_value, options=None):
    """Convert source_path into target_value and write it under OUTPUT_DIR.

    `options` carries the format-specific parameters collected from the request
    (see build_options). Returns a dict: name, path, mimeType, ext.
    """
    options = options or {}

    if not source_path or not os.path.exists(source_path):
        raise FileNotFoundError(f"FileConverter - Source file not found: {source_path}")

    target_ext = MIME_TO_EXT.get(target_value, target_value)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    base = os.path.splitext(os.path.basename(source_path))[0]
    out_name = f"{base}_{uuid.uuid4().hex[:8]}.{target_ext}"
    out_path = os.path.join(OUTPUT_DIR, out_name)

    src_ext = os.path.splitext(source_path)[1].lower().lstrip(".")

    if src_ext == target_ext:
        shutil.copyfile(source_path, out_path)
    elif target_ext in IMAGE_EXTS:
        _convert_image(source_path, out_path, target_ext, options)
    elif target_ext in DOCUMENT_EXTS and src_ext in IMAGE_EXTS:
        _convert_image_to_document(source_path, target_ext, out_path)
    elif target_ext in DOCUMENT_EXTS:
        _convert_document(source_path, target_ext, out_path)
    elif target_ext in PRINTER_EXTS:
        _convert_printer(source_path, out_path, target_ext, options)
    elif target_ext == "bin":
        shutil.copyfile(source_path, out_path)
    else:
        raise ValueError(f"FileConverter - Unsupported target format: {target_value}")

    if not os.path.exists(out_path):
        raise RuntimeError(
            f"FileConverter - Conversion produced no output: {source_path} -> {target_ext}"
        )

    return {
        "name": out_name,
        "path": out_path,
        "mimeType": EXT_TO_MIME.get(target_ext, "application/octet-stream"),
        "ext": target_ext,
    }


def _convert_image(source_path, out_path, target_ext, options):
    """Image -> image via Pillow, honouring quality / compression options."""
    img = PILImage.open(source_path)
    save_fmt = "JPEG" if target_ext in ("jpg", "jpeg") else target_ext.upper()
    save_kwargs = {}

    if save_fmt == "JPEG":
        # JPEG has no alpha channel; flatten transparency first.
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
        save_kwargs["quality"] = int(options.get("quality", 90))
    elif save_fmt == "WEBP":
        save_kwargs["quality"] = int(options.get("quality", 90))
    elif save_fmt == "PNG":
        save_kwargs["compress_level"] = int(options.get("compression", 6))

    img.save(out_path, save_fmt, **save_kwargs)


def _resolve_binary(*names):
    """Return the first binary name that exists on PATH, else None."""
    for name in names:
        if shutil.which(name):
            return name
    return None


def _convert_document(source_path, target_ext, out_path):
    """Document conversion via LibreOffice headless.

    Requires the `libreoffice`/`soffice` binary in the container. LibreOffice
    writes <base>.<ext> into the output dir; rename it to our unique out_path.
    """
    soffice = _resolve_binary("libreoffice", "soffice")
    if soffice is None:
        raise RuntimeError(
            "FileConverter - LibreOffice not found. Install it in the runtime "
            "(e.g. `apt-get install -y libreoffice` or `libreoffice-core`) so "
            "the `libreoffice`/`soffice` binary is on PATH."
        )

    out_dir = os.path.dirname(out_path)
    cmd = [soffice, "--headless", "--convert-to", target_ext, "--outdir", out_dir, source_path]

    print(f"[FileConverter] CMD: {' '.join(cmd)}", flush=True)
    print(f"[FileConverter] source exists: {os.path.exists(source_path)} | size: {os.path.getsize(source_path) if os.path.exists(source_path) else 'N/A'}", flush=True)

    before = set(os.listdir(out_dir))

    result = subprocess.run(cmd, capture_output=True, text=True)

    after = set(os.listdir(out_dir))
    new_files = after - before

    print(f"[FileConverter] returncode: {result.returncode}", flush=True)
    print(f"[FileConverter] stdout: {result.stdout.strip()}", flush=True)
    print(f"[FileConverter] stderr: {result.stderr.strip()}", flush=True)
    print(f"[FileConverter] new files in {out_dir}: {new_files}", flush=True)

    if result.returncode != 0:
        raise RuntimeError(
            f"FileConverter - LibreOffice failed (exit {result.returncode}).\n"
            f"CMD: {' '.join(cmd)}\n"
            f"STDOUT: {result.stdout.strip()}\n"
            f"STDERR: {result.stderr.strip()}"
        )

    produced = os.path.join(
        out_dir, os.path.splitext(os.path.basename(source_path))[0] + "." + target_ext
    )
    print(f"[FileConverter] expected produced path: {produced} | exists: {os.path.exists(produced)}", flush=True)

    if os.path.abspath(produced) == os.path.abspath(out_path):
        pass  # LibreOffice already wrote directly to out_path
    elif os.path.exists(produced):
        shutil.move(produced, out_path)
    elif new_files:
        # LibreOffice wrote a file but with an unexpected name — use that.
        actual = os.path.join(out_dir, next(iter(new_files)))
        print(f"[FileConverter] produced path mismatch — using actual: {actual}", flush=True)
        shutil.move(actual, out_path)
    else:
        raise RuntimeError(
            f"FileConverter - LibreOffice produced no output.\n"
            f"CMD: {' '.join(cmd)}\n"
            f"STDOUT: {result.stdout.strip()}\n"
            f"STDERR: {result.stderr.strip()}\n"
            f"Expected: {produced}"
        )


# Standard pixel dimensions at 300 DPI (industry reference).
# Point values are derived from these at render time so gs always produces
# exact integer pixel counts: pt = px * 72 / dpi  (e.g. 2480*72/300 = 595.2)
PAGE_PIXELS_300 = {
    "A4": (2480, 3508),
    "Letter": (2550, 3300),
}


def _page_points(page_key, dpi):
    """Return (width_pt, height_pt) that yield exact integer pixels at dpi."""
    base_w, base_h = PAGE_PIXELS_300.get(page_key, PAGE_PIXELS_300["A4"])
    scale = dpi / 300
    w_px = round(base_w * scale)
    h_px = round(base_h * scale)
    return (w_px * 72 / dpi, h_px * 72 / dpi)


def _printer_device(target_ext, is_color):
    """Pick the Ghostscript output device for a printer target + color mode.

    ps/urf/pcl/pclxl use devices that ship with vanilla Ghostscript. Only
    `pwgraster` requires a CUPS-enabled gs build (--enable-cups); verify with
    `gs -h | grep pwgraster` in the runtime. If pwgraster is missing, target
    `urf` instead — AirPrint printers accept image/urf as well.
    """
    if target_ext == "ps":
        return "ps2write"
    if target_ext == "pwg":
        return "pwgraster"                            # PWG Raster (CUPS build only)
    if target_ext == "urf":
        return "urfrgb" if is_color else "urfgray"    # Apple Raster / URF (native)
    if target_ext == "pcl":
        return "cljet5" if is_color else "ljet4"      # PCL5
    if target_ext == "pclxl":
        return "pxlcolor" if is_color else "pxlmono"  # PCL-XL / PCL6
    raise ValueError(f"FileConverter - Unsupported printer format: {target_ext}")



def _ensure_pdf(source_path):
    """Return a PDF path for source_path, converting first if necessary.

    Ghostscript printer devices consume PostScript/PDF, so non-PDF sources are
    turned into a temporary PDF (images via Pillow, documents via LibreOffice).
    """
    ext = os.path.splitext(source_path)[1].lower().lstrip(".")
    if ext in ("pdf", "ps"):
        return source_path

    base = os.path.splitext(os.path.basename(source_path))[0]
    pdf_path = os.path.join(tempfile.gettempdir(), f"{base}_{uuid.uuid4().hex[:8]}.pdf")

    if ext in IMAGE_EXTS:
        img = PILImage.open(source_path)
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
        img.save(pdf_path, "PDF")
    else:
        _convert_document(source_path, "pdf", pdf_path)

    return pdf_path


def _convert_printer(source_path, out_path, target_ext, options):
    """Printer/raster targets (ps, pwg, urf, pcl, pclxl) via Ghostscript.

    The source is normalised to PDF, then Ghostscript renders it with the right
    device and resolution; for raster/PCL targets the print-job options are
    passed through setpagedevice so the device builds a correct page header.
    """
    options = options or {}
    dpi = int(options.get("dpi", 300))
    color_space = int(options.get("color_space", 19))
    is_color = color_space == 19   # ConfigColorSpace: 19=sRGB, 18=sGray
    device = _printer_device(target_ext, is_color=is_color)

    gs = _resolve_binary("gs", "ghostscript")
    if gs is None:
        raise RuntimeError(
            "FileConverter - Ghostscript not found. Install it in the runtime "
            "(e.g. `apt-get install -y ghostscript`)."
        )

    pdf_source = _ensure_pdf(source_path)
    base = [gs, "-dNOPAUSE", "-dBATCH", "-dSAFER", f"-sDEVICE={device}", f"-r{dpi}"]

    if target_ext == "ps":
        cmd = base + [f"-sOutputFile={out_path}", pdf_source]
    else:
        # Exact point values computed from target pixel counts to prevent
        # the 1-pixel stride misalignment caused by integer rounding.
        w_pt, h_pt = _page_points(options.get("page_size", "A4"), dpi)
        geometry = [
            f"-dDEVICEWIDTHPOINTS={w_pt}",
            f"-dDEVICEHEIGHTPOINTS={h_pt}",
            "-dFIXEDMEDIA",
            "-dPDFFitPage",
        ]

        if target_ext == "pwg":
            # CUPS pwgraster device only. The printer advertises srgb_8 / sgray_8
            # (pwg-raster-document-type-supported), so cupsColorSpace must stay
            # 19 (sRGB, 24bpp) or 18 (sGray, 8bpp) — NOT plain RGB(1)/W(0).
            #
            # Do NOT set -sProcessColorModel here: the cups device derives its
            # colour model from cupsColorSpace, and forcing ProcessColorModel
            # makes gs reject sRGB with a rangecheck -> "Ghostscript failed
            # (exit 255)". cupsColorOrder=0 = chunky/packed (R G B R G B …).
            cups_color_space = 19 if is_color else 18
            cmd = base + geometry + [
                f"-dcupsColorSpace={cups_color_space}",
                "-dcupsBitsPerColor=8",
                "-dcupsColorOrder=0",
                f"-sOutputFile={out_path}",
                pdf_source,
            ]
        else:
            # urf (native urfrgb/urfgray) and pcl/pclxl: the colour model is
            # fixed by the device name itself, so cups* params and
            # ProcessColorModel don't apply (and forcing the latter errors on
            # mono devices such as ljet4/pxlmono/urfgray).
            cmd = base + geometry + [f"-sOutputFile={out_path}", pdf_source]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        combined = result.stdout + result.stderr
        if "Unknown device" in combined:
            raise RuntimeError(
                f"FileConverter - Ghostscript device '{device}' is not compiled into this build.\n"
                f"To enable it, the container needs a Ghostscript build that includes '{device}'.\n"
                f"Please choose a supported target format (e.g. PDF, PS, PCL)."
            )
        raise RuntimeError(
            f"FileConverter - Ghostscript failed (exit {result.returncode}):\n"
            f"CMD: {' '.join(cmd)}\n"
            f"STDERR: {result.stderr.strip()}\n"
            f"STDOUT: {result.stdout.strip()}"
        )


def md5_hash(file_path, chunk_size=8192):
    digest = hashlib.md5()
    with open(file_path, "rb") as file:
        while True:
            data = file.read(chunk_size)
            if not data:
                break
            digest.update(data)
    return digest.hexdigest()
