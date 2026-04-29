# OCRmyPDF-MCP

[Model Context Protocol](https://modelcontextprotocol.io) server that wraps
[OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF). Adds searchable text layers
to PDFs from any MCP-compatible client (LM Studio, Claude Desktop, etc.).

## Prerequisites

- Python 3.10+
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
- [Ghostscript](https://www.ghostscript.com/)

### Install Tesseract (Windows)

```
winget install UB-Mannheim.TesseractOCR
```

### Install Ghostscript (Windows)

```
winget install ArtifexSoftware.GhostScript
```

The server auto-detects Tesseract under `C:\Program Files\Tesseract-OCR\` on
Windows and adds it to `PATH` at startup, so no extra config is needed.

## Run with `uvx` (recommended)

No clone, no `pip install` — `uvx` handles environment isolation:

### LM Studio

```json
{
  "mcpServers": {
    "ocrmypdf": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/enmito/OCRmyPDF-MCP#subdirectory=mcp",
        "ocrmypdf-mcp"
      ]
    }
  }
}
```

### Claude Desktop

`%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ocrmypdf": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/enmito/OCRmyPDF-MCP#subdirectory=mcp",
        "ocrmypdf-mcp"
      ]
    }
  }
}
```

## Run from a local clone

```bash
git clone https://github.com/enmito/OCRmyPDF-MCP
cd OCRmyPDF-MCP/mcp
pip install -e .
ocrmypdf-mcp        # starts the server on stdio
```

## Tools exposed

### `ocr_pdf`

Run OCR on a local PDF file.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `input_path` | string | yes | Absolute path to the input PDF |
| `output_path` | string | | Output path (default: `<input>.ocr.pdf`) |
| `language` | string | | Tesseract language code(s), e.g. `eng`, `deu`, `eng+deu`. Default: `eng` |
| `deskew` | bool | | Straighten skewed pages |
| `rotate_pages` | bool | | Auto-rotate pages |
| `clean` | bool | | Pre-process with unpaper |
| `force_ocr` | bool | | Re-OCR pages that already have text |
| `skip_text` | bool | | Skip pages that already have text |
| `optimize` | int (0–3) | | Optimization level (default: 1) |
| `output_type` | string | | `pdf`, `pdfa`, `pdfa-2`, `pdfa-3` |
| `sidecar` | string | | Path to save extracted plain text alongside the PDF |

Example prompt:

> OCR `D:/scans/manual.pdf` and save the result as `D:/scans/manual_ocr.pdf`.

### `ocr_pdf_base64`

Accept a Base64-encoded PDF, run OCR, return the result as Base64. Use this
when the client and server don't share a filesystem.

### `get_ocr_languages`

List all Tesseract language packs installed on this system.

## Adding extra Tesseract languages

Tesseract ships with English (`eng`) by default. For other languages, drop the
corresponding `.traineddata` file from
[tessdata_fast](https://github.com/tesseract-ocr/tessdata_fast) into your
Tesseract `tessdata/` directory (typically `C:\Program Files\Tesseract-OCR\tessdata\`,
requires admin rights to write there) — then call the OCR tool with that
language code.

## Troubleshooting

**`tesseract not found`** — install Tesseract and ensure it's at one of the
common locations (the server auto-detects `C:\Program Files\Tesseract-OCR\`).

**Ghostscript errors** — install Ghostscript and verify it's on `PATH`.

**`WinError 2` warnings during OCR** — harmless. They mean optional
optimization tools (`jbig2`, `pngquant`, `unpaper`) aren't installed; OCR still
completes.

## License

MPL-2.0, same as the upstream OCRmyPDF project.
