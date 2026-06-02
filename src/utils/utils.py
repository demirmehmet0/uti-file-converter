
import os
import uuid
import shutil
import hashlib
import tempfile
import urllib.request
import subprocess

from PIL import Image as PILImage

from sdks.novavision.src.helper.package import PackageHelper

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

    if target_ext in IMAGE_EXTS:
        _convert_image(source_path, out_path, target_ext, options)
    elif target_ext in DOCUMENT_EXTS:
        _convert_document(source_path, target_ext, out_path)
    elif target_ext in PRINTER_EXTS:
        _convert_printer(source_path, out_path, target_ext, options)
    elif target_ext == "bin":
        shutil.copyfile(source_path, out_path)  # raw passthrough
    else:
        raise ValueError(f"FileConverter - Unsupported target format: {target_value}")

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
    subprocess.run(
        [soffice, "--headless", "--convert-to", target_ext,
         "--outdir", out_dir, source_path],
        check=True, capture_output=True,
    )
    produced = os.path.join(
        out_dir, os.path.splitext(os.path.basename(source_path))[0] + "." + target_ext
    )
    if os.path.abspath(produced) != os.path.abspath(out_path) and os.path.exists(produced):
        shutil.move(produced, out_path)


# Physical page sizes in PostScript points (1/72 inch).
PAGE_SIZES_PT = {
    "A4": (595, 842),
    "Letter": (612, 792),
}


def _printer_device(target_ext, is_color):
    """Pick the Ghostscript output device for a printer target + color mode.

    All of these ship with Ghostscript itself, so no cups-filters is needed.
    Verify availability in the runtime with `gs -h` if a target errors.
    """
    if target_ext == "ps":
        return "ps2write"
    if target_ext == "pwg":
        return "pwgraster"          # PWG Raster (color via ProcessColorModel)
    if target_ext == "urf":
        return "appleraster"        # Apple Raster / URF
    if target_ext == "pcl":
        return "cljet5" if is_color else "ljet4"    # PCL5
    if target_ext == "pclxl":
        return "pxlcolor" if is_color else "pxlmono"  # PCL-XL / PCL6
    raise ValueError(f"FileConverter - Unsupported printer format: {target_ext}")


def _setpagedevice(options):
    """Build a PostScript setpagedevice snippet from the print-job options.

    Ghostscript's raster devices fold these keys into the CUPS/PWG page header,
    so resolution + page size produce a correctly aligned raster (cupsWidth and
    cupsBytesPerLine are computed by the device, which avoids stride drift).
    """
    color_space = int(options.get("color_space", 19))
    is_color = color_space == 19  # 19 = sRGB, 18 = Sgray
    page = PAGE_SIZES_PT.get(options.get("page_size", "A4"), PAGE_SIZES_PT["A4"])
    duplex = int(options.get("duplex", 0))
    media_type = {0: "stationery", 1: "photographic"}.get(int(options.get("media_type", 0)), "stationery")

    parts = [
        f"/PageSize [{page[0]} {page[1]}]",
        f"/ProcessColorModel /{'DeviceRGB' if is_color else 'DeviceGray'}",
        f"/Duplex {'true' if duplex in (1, 2) else 'false'}",
        f"/Tumble {'true' if duplex == 2 else 'false'}",
        f"/MediaPosition {int(options.get('media_position', 0))}",
        f"/MediaType ({media_type})",
    ]
    return "<< " + " ".join(parts) + " >> setpagedevice"


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
    color_space = int(options.get("color_space", 19))
    device = _printer_device(target_ext, is_color=(color_space == 19))

    gs = _resolve_binary("gs", "ghostscript")
    if gs is None:
        raise RuntimeError(
            "FileConverter - Ghostscript not found. Install it in the runtime "
            "(e.g. `apt-get install -y ghostscript`)."
        )

    pdf_source = _ensure_pdf(source_path)
    dpi = int(options.get("dpi", 300))
    cmd = [gs, "-dNOPAUSE", "-dBATCH", "-dSAFER",
           f"-sDEVICE={device}", f"-r{dpi}", f"-sOutputFile={out_path}"]

    if target_ext == "ps":
        cmd += [pdf_source]  # ps2write does not rasterize; page-device hints n/a
    else:
        cmd += ["-c", _setpagedevice(options), "-f", pdf_source]

    subprocess.run(cmd, check=True, capture_output=True)


def md5_hash(file_path, chunk_size=8192):
    digest = hashlib.md5()
    with open(file_path, "rb") as file:
        while True:
            data = file.read(chunk_size)
            if not data:
                break
            digest.update(data)
    return digest.hexdigest()
