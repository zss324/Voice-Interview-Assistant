from __future__ import annotations

from pathlib import Path

MAX_RESUME_CHARS = 50000


def extract_resume_text(path: str | Path) -> str:
    """Extract selectable text; scanned PDFs are intentionally unsupported."""
    import pymupdf

    pdf_path = Path(path)
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("请选择 PDF 简历。")
    with pymupdf.open(pdf_path) as document:
        if document.is_encrypted:
            raise ValueError("简历 PDF 已加密，请先解除密码保护。")
        text = "\n\n".join(page.get_text("text", sort=True) for page in document)
    text = text.strip()
    if not text:
        raise ValueError("未提取到文字；请使用可选中文字的 PDF 简历。")
    if len(text) > MAX_RESUME_CHARS:
        raise ValueError("简历文字过长，请先精简至 5 万字以内。")
    return text
