from pathlib import Path

import pytest
from docx import Document
from pypdf import PdfWriter


@pytest.fixture
def pdf_file(tmp_path: Path) -> Path:
    path = tmp_path / "example-input.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with path.open("wb") as stream:
        writer.write(stream)
    return path


@pytest.fixture
def output_file(tmp_path: Path) -> Path:
    return tmp_path / "converted.docx"


@pytest.fixture
def write_valid_docx():
    def _write(path: Path) -> None:
        document = Document()
        document.add_paragraph("example.com fixture")
        document.save(path)

    return _write
