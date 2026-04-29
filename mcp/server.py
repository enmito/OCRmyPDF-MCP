#!/usr/bin/env python3
"""MCP server wrapping OCRmyPDF — stdio transport, compatible with LM Studio and Claude Desktop."""

import asyncio
import base64
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# --- Tesseract auto-detection (Windows) ---
_TESSERACT_CANDIDATES = [
    r"C:\Program Files\Tesseract-OCR",
    r"C:\Program Files (x86)\Tesseract-OCR",
    r"C:\Users\{username}\AppData\Local\Programs\Tesseract-OCR",
]

def _setup_tesseract() -> None:
    """Add Tesseract to PATH and set TESSDATA_PREFIX if not already configured."""
    if sys.platform != "win32":
        return

    path_env = os.environ.get("PATH", "")
    tessdata_set = bool(os.environ.get("TESSDATA_PREFIX"))

    for candidate in _TESSERACT_CANDIDATES:
        candidate = candidate.replace("{username}", os.environ.get("USERNAME", ""))
        p = Path(candidate)
        if (p / "tesseract.exe").exists():
            if str(p) not in path_env:
                os.environ["PATH"] = str(p) + os.pathsep + path_env
            if not tessdata_set:
                td = p / "tessdata"
                if td.exists():
                    os.environ["TESSDATA_PREFIX"] = str(td)
            break

_setup_tesseract()

import ocrmypdf  # noqa: E402 — must come after PATH is configured
from mcp.server.fastmcp import FastMCP  # noqa: E402

mcp = FastMCP("ocrmypdf")


@mcp.tool()
async def ocr_pdf(
    input_path: str,
    output_path: str = "",
    language: str = "eng",
    deskew: bool = False,
    rotate_pages: bool = False,
    clean: bool = False,
    force_ocr: bool = False,
    skip_text: bool = False,
    optimize: int = 1,
    output_type: str = "pdf",
    sidecar: str = "",
) -> str:
    """
    Run OCR on a PDF file and save the result.

    Args:
        input_path: Absolute path to the input PDF file.
        output_path: Absolute path for the output PDF. Omit to save as <input>.ocr.pdf.
        language: Tesseract language code(s), e.g. 'eng', 'deu', 'eng+deu'. Default: 'eng'.
        deskew: Deskew (straighten) scanned pages.
        rotate_pages: Auto-rotate pages to correct orientation.
        clean: Clean pages with unpaper before OCR.
        force_ocr: Force re-OCR even if the PDF already has text.
        skip_text: Skip pages that already have text.
        optimize: Optimization level 0-3 (0=none, 3=max). Default: 1.
        output_type: Output format: 'pdf', 'pdfa', 'pdfa-2', 'pdfa-3'. Default: 'pdf'.
        sidecar: Optional path to save extracted plain text alongside the PDF.
    """
    src = Path(input_path)
    if not src.exists():
        return f"Error: Input file not found: {src}"

    dst = Path(output_path) if output_path else src.with_suffix(".ocr.pdf")
    dst.parent.mkdir(parents=True, exist_ok=True)

    kwargs = _build_kwargs(language, deskew, rotate_pages, clean, force_ocr, skip_text, optimize, output_type, sidecar)
    try:
        exit_code = await asyncio.to_thread(ocrmypdf.ocr, str(src), str(dst), **kwargs)
        return f"OCR complete (exit={exit_code.name}). Output: {dst}"
    except Exception as e:
        return f"OCR failed: {e}"


@mcp.tool()
async def ocr_pdf_base64(
    pdf_base64: str,
    language: str = "eng",
    deskew: bool = False,
    rotate_pages: bool = False,
    force_ocr: bool = False,
    output_type: str = "pdf",
) -> str:
    """
    Accept a Base64-encoded PDF, run OCR, and return the result as Base64.
    Useful when working without shared filesystem access.

    Args:
        pdf_base64: Base64-encoded content of the input PDF.
        language: Tesseract language code(s). Default: 'eng'.
        deskew: Deskew pages.
        rotate_pages: Auto-rotate pages.
        force_ocr: Force re-OCR even if text already exists.
        output_type: Output format. Default: 'pdf'.
    """
    try:
        pdf_bytes = base64.b64decode(pdf_base64)
    except Exception as e:
        return f"Error: Invalid base64: {e}"

    kwargs = _build_kwargs(language, deskew, rotate_pages, False, force_ocr, False, 1, output_type, "")
    input_tmp = output_tmp = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fin:
            fin.write(pdf_bytes)
            input_tmp = fin.name
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fout:
            output_tmp = fout.name

        exit_code = await asyncio.to_thread(ocrmypdf.ocr, input_tmp, output_tmp, **kwargs)
        with open(output_tmp, "rb") as f:
            result_b64 = base64.b64encode(f.read()).decode()
        return f"OCR complete (exit={exit_code.name}). Result base64:\n{result_b64}"
    except Exception as e:
        return f"OCR failed: {e}"
    finally:
        for p in [input_tmp, output_tmp]:
            if p:
                try:
                    os.unlink(p)
                except Exception:
                    pass


@mcp.tool()
async def get_ocr_languages() -> str:
    """List all Tesseract OCR language packs installed on this system."""
    try:
        result = await asyncio.to_thread(
            subprocess.run,
            ["tesseract", "--list-langs"],
            capture_output=True,
            text=True,
        )
        output = result.stdout + result.stderr
        langs = [ln.strip() for ln in output.splitlines() if ln.strip() and not ln.startswith("List")]
        return "Installed languages:\n" + "\n".join(langs)
    except FileNotFoundError:
        return "Error: tesseract not found. Install from https://github.com/UB-Mannheim/tesseract/wiki"


def _build_kwargs(
    language: str,
    deskew: bool,
    rotate_pages: bool,
    clean: bool,
    force_ocr: bool,
    skip_text: bool,
    optimize: int,
    output_type: str,
    sidecar: str,
) -> dict:
    langs = language.split("+") if "+" in language else [language]
    kwargs: dict = {"language": langs, "optimize": optimize, "output_type": output_type}
    if deskew:
        kwargs["deskew"] = True
    if rotate_pages:
        kwargs["rotate_pages"] = True
    if clean:
        kwargs["clean"] = True
    if force_ocr:
        kwargs["force_ocr"] = True
    if skip_text:
        kwargs["skip_text"] = True
    if sidecar:
        kwargs["sidecar"] = sidecar
    return kwargs


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
