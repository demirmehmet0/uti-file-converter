# FileConverter

Component for NOVAVISION.

Converts a source document/image into a target format selected in the config.
The converted file is written under `/storage/FileConverter/` and its path is
returned as the output, so a downstream package (e.g. FileSave) can pick it up.

## Executors

| Executor | Source of the file |
|----------|--------------------|
| `FromInput` | Receives the file from the previous package's output (`inputFile`) |
| `FromStorage` | Reads the file selected through the `filePicker` config widget |

Both executors take a `ConfigTargetFormat` dropdown and emit an `outputFile`.

## Target formats

Extension-based (`pdf`, `docx`, `txt`, `png`, `jpg`, `webp`) and MIME-based
(`application/pdf`, `image/jpeg`, `image/pwg-raster`, `image/urf`,
`application/vnd.hp-pcl`, `application/pcl`, `application/postscript`,
`application/vnd.hp-pclxl`, `application/octet-stream`).

## Conversion backends

- **Images** — Pillow
- **Documents** (pdf/docx/txt/…) — LibreOffice headless (`libreoffice` binary)
- **PostScript** — Ghostscript (`gs` binary)
- **PCL / PCL-XL / PWG-raster / URF** — require `cups-filters`; not yet wired

## Run

```bash
python FileConverter/src/executors/FromInput.py '<config_json>'
python FileConverter/src/executors/FromStorage.py '<config_json>'
```
