"""PDF text extraction helpers for the reader workflow."""

from __future__ import annotations

from io import BytesIO


class PDFTextExtractionError(ValueError):
    """Raised when a PDF cannot be decoded into usable text."""


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes using pypdf.

    The dependency is intentionally isolated here so the API can return a
    controlled error if PDF support is unavailable or the file is invalid.
    """
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - exercised only in broken envs
        raise PDFTextExtractionError("当前环境缺少 pypdf，无法解析 PDF。") from exc

    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        page_texts = [(page.extract_text() or "").strip() for page in reader.pages]
    except Exception as exc:  # pypdf raises several parser-specific exceptions
        raise PDFTextExtractionError("PDF 解析失败，请确认文件未损坏且包含可复制文本。") from exc

    text = "\n\n".join(page for page in page_texts if page)
    if not text.strip():
        raise PDFTextExtractionError("未能从 PDF 中提取正文，请确认 PDF 不是纯扫描图片。")
    return text
