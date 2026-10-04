"""Фабрика DocumentConverter с обходом бага docling-parse на Windows (пути с кириллицей)."""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat


def _default_pdf_backend() -> str:
    env = (os.getenv("DOCLING_PDF_BACKEND") or "").strip().lower()
    if env in {"pypdfium2", "docling_parse"}:
        return env
    if sys.platform == "win32":
        return "pypdfium2"
    return "docling_parse"


def create_document_converter() -> DocumentConverter:
    backend_name = _default_pdf_backend()

    if backend_name == "pypdfium2":
        from docling.backend.pdf_backend import PdfBackendOptions
        from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend

        pdf_option = PdfFormatOption(
            backend=PyPdfiumDocumentBackend,
            backend_options=PdfBackendOptions(),
        )
    else:
        pdf_option = PdfFormatOption()

    return DocumentConverter(
        format_options={
            InputFormat.PDF: pdf_option,
        }
    )


def write_upload_temp_file(file_bytes: bytes, file_name: str) -> Path:
    """Пишет файл в ASCII-путь (%LOCALAPPDATA%), чтобы нативные парсеры не ломались."""
    suffix = Path(file_name).suffix.lower() or ".bin"
    base = Path(os.environ.get("LOCALAPPDATA", os.environ.get("TEMP", ".")))
    temp_dir = base / "vpg07_docling"
    temp_dir.mkdir(parents=True, exist_ok=True)
    path = temp_dir / f"{uuid.uuid4().hex}{suffix}"
    path.write_bytes(file_bytes)
    return path
