from pathlib import Path

import pytest


def test_no_ocr는_ocrmyPDF를_호출하지않고_pdf2docx를_호출한다(pdf_file, output_file, monkeypatch, write_valid_docx):
    from document_convert.converter import convert

    calls = []
    monkeypatch.setattr("document_convert.converter.run_ocr", lambda *args, **kwargs: calls.append("ocr"))
    monkeypatch.setattr("document_convert.converter.run_pdf2docx", lambda source, target, **kwargs: (calls.append("docx"), write_valid_docx(target)))

    convert(pdf_file, output_file, no_ocr=True, lang="kor+eng", timeout=300)

    assert calls == ["docx"]
    assert output_file.exists()


def test_ocr는_언어와_시간제한을_전달한다(pdf_file, output_file, monkeypatch, write_valid_docx):
    from document_convert.converter import convert

    received = {}
    monkeypatch.setattr("document_convert.converter.run_ocr", lambda source, target, **kwargs: received.update(kwargs) or target.write_bytes(pdf_file.read_bytes()))
    monkeypatch.setattr("document_convert.converter.run_pdf2docx", lambda source, target, **kwargs: write_valid_docx(target))

    convert(pdf_file, output_file, no_ocr=False, lang="eng", timeout=17)

    assert received["lang"] == "eng"
    assert received["timeout"] == 17


def test_ocr_언어팩이_없으면_명확한_오류를_낸다(pdf_file, output_file, monkeypatch):
    from document_convert.converter import MissingLanguageError, convert

    monkeypatch.setattr("document_convert.converter.available_languages", lambda: {"eng"})
    with pytest.raises(MissingLanguageError, match="kor"):
        convert(pdf_file, output_file, lang="kor+eng")
    assert not output_file.exists()


def test_사용가능언어를_확인할수없으면_ocr전에_언어팩오류다(pdf_file, output_file, monkeypatch):
    from document_convert.converter import MissingLanguageError, convert

    monkeypatch.setattr("document_convert.converter.available_languages", lambda: None)
    monkeypatch.setattr("document_convert.converter.run_ocr", lambda *args, **kwargs: pytest.fail("OCR하면 안 됨"))
    with pytest.raises(MissingLanguageError):
        convert(pdf_file, output_file, lang="kor+eng")


def test_시간초과시_부분출력을_남기지않는다(pdf_file, output_file, monkeypatch):
    from document_convert.converter import ConversionTimeoutError, convert

    def timeout(*args, **kwargs):
        raise TimeoutError("timed out")

    monkeypatch.setattr("document_convert.converter.run_ocr", timeout)
    with pytest.raises(ConversionTimeoutError):
        convert(pdf_file, output_file, timeout=1)
    assert not output_file.exists()
    assert not list(output_file.parent.glob(".*.docx"))


def test_변환실패시_기존출력을_보호한다(pdf_file, output_file, monkeypatch):
    from document_convert.converter import ConversionError, convert

    output_file.write_bytes(b"old")
    monkeypatch.setattr("document_convert.converter.run_pdf2docx", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("bad pdf")))
    with pytest.raises(ConversionError):
        convert(pdf_file, output_file, no_ocr=True)
    assert output_file.read_bytes() == b"old"


def test_입력과_출력이_같으면_변환전에_거부한다(pdf_file, monkeypatch):
    from document_convert.converter import ConversionError, convert

    monkeypatch.setattr("document_convert.converter.run_pdf2docx", lambda *args, **kwargs: pytest.fail("변환하면 안 됨"))
    with pytest.raises(ConversionError, match="same|identical|같"):
        convert(pdf_file, pdf_file, no_ocr=True)


def test_기존출력은_overwrite가_없으면_직접변환에서도_보호한다(pdf_file, output_file, monkeypatch):
    from document_convert.converter import ConversionError, convert

    output_file.write_bytes(b"old")
    monkeypatch.setattr("document_convert.converter.run_pdf2docx", lambda *args, **kwargs: pytest.fail("변환하면 안 됨"))
    with pytest.raises(ConversionError, match="exist|overwrite"):
        convert(pdf_file, output_file, no_ocr=True)
    assert output_file.read_bytes() == b"old"


def test_overwrite를_명시하면_기존출력을_교체한다(pdf_file, output_file, monkeypatch, write_valid_docx):
    from document_convert.converter import convert

    output_file.write_bytes(b"old")
    monkeypatch.setattr("document_convert.converter.run_pdf2docx", lambda source, target, **kwargs: write_valid_docx(target))
    convert(pdf_file, output_file, no_ocr=True, overwrite=True)
    assert output_file.read_bytes() != b"old"


def test_출력부모디렉터리가_없으면_ConversionError다(pdf_file, tmp_path, monkeypatch):
    from document_convert.converter import ConversionError, convert

    target = tmp_path / "missing-parent" / "result.docx"
    with pytest.raises(ConversionError):
        convert(pdf_file, target, no_ocr=True)
    assert not target.exists()


def test_암호화된_pdf는_변환전에_거부한다(pdf_file, output_file, monkeypatch):
    from document_convert.converter import EncryptedPdfError, convert

    class FakeReader:
        is_encrypted = True

    monkeypatch.setattr("document_convert.converter.PdfReader", lambda *args, **kwargs: FakeReader())
    with pytest.raises(EncryptedPdfError):
        convert(pdf_file, output_file, no_ocr=True)


def test_손상된_pdf는_ConversionError다(pdf_file, output_file, monkeypatch):
    from document_convert.converter import ConversionError, convert

    monkeypatch.setattr("document_convert.converter.PdfReader", lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("invalid pdf")))
    with pytest.raises(ConversionError):
        convert(pdf_file, output_file, no_ocr=True)


def test_실제_malformed_xref_pdf는_엄격한_파싱으로_거부한다(tmp_path):
    from document_convert.converter import ConversionError, convert

    source = tmp_path / "malformed.pdf"
    source.write_bytes(b"%PDF-1.4\n1 0 obj<<>>endobj\nxref\nnot-a-valid-xref\n%%EOF\n")
    with pytest.raises(ConversionError):
        convert(source, tmp_path / "malformed.docx", no_ocr=True)


def test_pdfreader는_strict_true로_호출된다(pdf_file, output_file, monkeypatch):
    from document_convert.converter import ConversionError, convert

    received = {}

    def fake_reader(*args, **kwargs):
        received.update(kwargs)
        raise ValueError("invalid pdf")

    monkeypatch.setattr("document_convert.converter.PdfReader", fake_reader)
    with pytest.raises(ConversionError):
        convert(pdf_file, output_file, no_ocr=True)
    assert received["strict"] is True


def test_실제_pdf2docx와_pymupdf로_텍스트_pdf를_docx로_변환한다(tmp_path):
    fitz = pytest.importorskip("fitz")
    pytest.importorskip("pdf2docx")
    from docx import Document
    from document_convert.converter import convert

    source = tmp_path / "synthetic-text.pdf"
    document = fitz.open()
    page = document.new_page(width=612, height=792)
    page.insert_text((72, 100), "Synthetic example.com integration text")
    document.save(source)
    document.close()
    target = tmp_path / "synthetic-text.docx"

    convert(source, target, no_ocr=True)

    assert target.exists()
    converted = Document(target)
    text = "\n".join(paragraph.text for paragraph in converted.paragraphs)
    assert "Synthetic" in text
    assert "example.com" in text
