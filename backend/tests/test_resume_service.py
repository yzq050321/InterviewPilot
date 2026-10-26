"""V2.2 resume extraction tests; no network, no database, no original file storage."""
from io import BytesIO

import pytest
from docx import Document

from app.resume_service import (
    MAX_RESUME_BYTES,
    ResumeParseError,
    extract_resume_text,
)


def make_docx(text: str) -> bytes:
    document = Document()
    document.add_paragraph(text)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_docx_extracts_text_and_metadata():
    data = make_docx(
        "张三，Python 后端实习生。项目使用 FastAPI、MySQL、SQLAlchemy 和 LangChain，"
        "负责接口设计、数据库建模与自动化测试，熟悉 Docker 与 Git。"
    )
    parsed = extract_resume_text("张三-简历.docx", data)
    assert "FastAPI" in parsed.text
    assert "LangChain" in parsed.text
    assert parsed.filename == "张三-简历.docx"
    assert parsed.pages is None


def test_unsupported_extension_is_rejected():
    with pytest.raises(ResumeParseError, match="PDF 或 DOCX"):
        extract_resume_text("resume.txt", b"plain text")


def test_empty_file_is_rejected():
    with pytest.raises(ResumeParseError, match="为空"):
        extract_resume_text("resume.pdf", b"")


def test_oversized_file_is_rejected_before_parsing():
    data = b"%PDF-" + b"0" * MAX_RESUME_BYTES
    with pytest.raises(ResumeParseError, match="5 MB"):
        extract_resume_text("resume.pdf", data)


def test_invalid_pdf_magic_is_rejected():
    with pytest.raises(ResumeParseError, match="有效的 PDF"):
        extract_resume_text("resume.pdf", b"not a pdf")


def test_filename_path_is_stripped():
    data = make_docx("Python FastAPI MySQL 项目经验，负责接口、数据库和自动化测试。")
    parsed = extract_resume_text(r"..\..\secret\resume.docx", data)
    assert parsed.filename == "resume.docx"
