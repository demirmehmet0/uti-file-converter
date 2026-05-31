
import os
import uuid
import shutil
import hashlib
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


def convert_file(source_path, target_value):
    """Convert source_path into target_value and write it under OUTPUT_DIR.

    Returns a dict describing the produced file: name, path, mimeType, ext.
    """
    if not source_path or not os.path.exists(source_path):
        raise FileNotFoundError(f"FileConverter - Source file not found: {source_path}")

    target_ext = MIME_TO_EXT.get(target_value, target_value)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    base = os.path.splitext(os.path.basename(source_path))[0]
    out_name = f"{base}_{uuid.uuid4().hex[:8]}.{target_ext}"
    out_path = os.path.join(OUTPUT_DIR, out_name)

    if target_ext in IMAGE_EXTS:
        _convert_image(source_path, out_path, target_ext)
    elif target_ext in DOCUMENT_EXTS:
        _convert_document(source_path, target_ext, out_path)
    elif target_ext in PRINTER_EXTS:
        _convert_printer(source_path, out_path, target_ext)
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


def _convert_image(source_path, out_path, target_ext):
    """Image -> image via Pillow."""
    img = PILImage.open(source_path)
    save_fmt = "JPEG" if target_ext in ("jpg", "jpeg") else target_ext.upper()
    # JPEG/BMP have no alpha channel; flatten transparency before saving.
    if save_fmt in ("JPEG", "BMP") and img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGB")
    img.save(out_path, save_fmt)


def _convert_document(source_path, target_ext, out_path):
    """Document conversion via LibreOffice headless.

    Requires the `libreoffice`/`soffice` binary in the container. LibreOffice
    writes <base>.<ext> into the output dir; rename it to our unique out_path.
    """
    out_dir = os.path.dirname(out_path)
    subprocess.run(
        ["libreoffice", "--headless", "--convert-to", target_ext,
         "--outdir", out_dir, source_path],
        check=True, capture_output=True,
    )
    produced = os.path.join(
        out_dir, os.path.splitext(os.path.basename(source_path))[0] + "." + target_ext
    )
    if os.path.abspath(produced) != os.path.abspath(out_path) and os.path.exists(produced):
        shutil.move(produced, out_path)


def _convert_printer(source_path, out_path, target_ext):
    """Printer/raster targets.

    PostScript is produced with Ghostscript. PCL/PCL-XL/PWG-raster/URF require
    cups-filters (e.g. pdftoraster, rastertopclx) and are not wired yet.
    """
    if target_ext == "ps":
        subprocess.run(
            ["gs", "-dNOPAUSE", "-dBATCH", "-sDEVICE=ps2write",
             f"-sOutputFile={out_path}", source_path],
            check=True, capture_output=True,
        )
    else:
        raise NotImplementedError(
            f"FileConverter - '{target_ext}' output requires cups-filters; not yet wired."
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
