from pathlib import Path

import pymupdf

from src.modules.resume import extract_resume_text


def test_extracts_selectable_pdf_text(tmp_path: Path):
    file = tmp_path / "resume.pdf"
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Java engineer")
    document.save(file)
    document.close()
    assert "Java engineer" in extract_resume_text(file)
