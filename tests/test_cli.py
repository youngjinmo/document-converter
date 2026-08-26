from pathlib import Path

import pytest


def invoke(argv, monkeypatch):
    from document_convert.cli import main

    monkeypatch.setattr("sys.argv", ["document-convert", *argv])
    return main()


def test_변환_성공시_기본출력파일을_생성한다(pdf_file, tmp_path, monkeypatch):
    output = tmp_path / "example-input.docx"
    monkeypatch.setattr("document_convert.cli.convert", lambda source, target, **kwargs: target.write_bytes(b"PK"))

    result = invoke([str(pdf_file)], monkeypatch)

    assert result == 0
    assert output.exists()


def test_o_옵션으로_출력경로를_지정한다(pdf_file, output_file, monkeypatch):
    monkeypatch.setattr("document_convert.cli.convert", lambda source, target, **kwargs: target.write_bytes(b"PK"))

    assert invoke([str(pdf_file), "-o", str(output_file)], monkeypatch) == 0
    assert output_file.exists()


def test_기존출력은_overwrite_없으면_실패한다(pdf_file, output_file, monkeypatch, capsys):
    output_file.write_bytes(b"existing")
    monkeypatch.setattr("document_convert.cli.convert", lambda *args, **kwargs: pytest.fail("변환하면 안 됨"))

    assert invoke([str(pdf_file), "-o", str(output_file)], monkeypatch) == 2
    assert output_file.read_bytes() == b"existing"
    assert "overwrite" in capsys.readouterr().err.lower()


def test_overwrite_지정시_기존출력을_교체한다(pdf_file, output_file, monkeypatch):
    output_file.write_bytes(b"existing")
    monkeypatch.setattr("document_convert.cli.convert", lambda source, target, **kwargs: target.write_bytes(b"PK"))

    assert invoke([str(pdf_file), "-o", str(output_file), "--overwrite"], monkeypatch) == 0
    assert output_file.read_bytes() == b"PK"


@pytest.mark.parametrize("option", ["--lang", "--timeout"])
def test_옵션값이_누락되면_사용법오류다(pdf_file, option, monkeypatch):
    with pytest.raises(SystemExit) as error:
        invoke([str(pdf_file), option], monkeypatch)
    assert error.value.code == 2


def test_존재하지않는_입력은_실패하고_출력을_만들지않는다(tmp_path, output_file, monkeypatch):
    monkeypatch.setattr("document_convert.cli.convert", lambda *args, **kwargs: pytest.fail("변환하면 안 됨"))

    assert invoke([str(tmp_path / "missing.pdf"), "-o", str(output_file)], monkeypatch) == 2
    assert not output_file.exists()


def test_pdf가_아닌_입력은_실패한다(tmp_path, output_file, monkeypatch):
    source = tmp_path / "input.txt"
    source.write_text("not a PDF", encoding="utf-8")
    monkeypatch.setattr("document_convert.cli.convert", lambda *args, **kwargs: pytest.fail("변환하면 안 됨"))

    assert invoke([str(source), "-o", str(output_file)], monkeypatch) == 2
    assert not output_file.exists()


def test_기본값은_kor_eng_ocr과_300초다(pdf_file, output_file, monkeypatch):
    received = {}

    def fake_convert(source, target, **kwargs):
        received.update(kwargs)
        target.write_bytes(b"PK")

    monkeypatch.setattr("document_convert.cli.convert", fake_convert)
    assert invoke([str(pdf_file), "-o", str(output_file)], monkeypatch) == 0
    assert received["lang"] == "kor+eng"
    assert received["timeout"] == 300


def test_markdown_출력확장자를_허용하고_변환기에_전달한다(pdf_file, tmp_path, monkeypatch):
    output = tmp_path / "result.md"
    received = {}

    def fake_convert(source, target, **kwargs):
        received.update(kwargs)
        target.write_text("# converted", encoding="utf-8")

    monkeypatch.setattr("document_convert.cli.convert", fake_convert)

    assert invoke([str(pdf_file), "-o", str(output)], monkeypatch) == 0
    assert output.read_text(encoding="utf-8") == "# converted"
    assert received["overwrite"] is False


def test_출력확장자는_대소문자를_구분하지_않는다(pdf_file, tmp_path, monkeypatch):
    for suffix in (".MD", ".DOCX"):
        output = tmp_path / f"result{suffix}"
        monkeypatch.setattr(
            "document_convert.cli.convert",
            lambda source, target, **kwargs: target.write_text("ok", encoding="utf-8"),
        )

        assert invoke([str(pdf_file), "-o", str(output)], monkeypatch) == 0
        assert output.exists()


def test_no_ocr_플래그를_변환기에_전달한다(pdf_file, output_file, monkeypatch):
    received = {}
    monkeypatch.setattr(
        "document_convert.cli.convert",
        lambda source, target, **kwargs: (received.update(kwargs), target.write_bytes(b"PK")),
    )

    assert invoke([str(pdf_file), "-o", str(output_file), "--no-ocr"], monkeypatch) == 0
    assert received["no_ocr"] is True


@pytest.mark.parametrize("output_name", ["result.pdf", "result", "result.DOC", "result.html"])
def test_지원하지_않는_출력확장자는_거부한다(pdf_file, tmp_path, output_name, monkeypatch):
    monkeypatch.setattr("document_convert.cli.convert", lambda *args, **kwargs: pytest.fail("변환하면 안 됨"))

    assert invoke([str(pdf_file), "-o", str(tmp_path / output_name)], monkeypatch) == 2


def test_도움말에_애플리케이션명과_dc_사용법이_표시된다(monkeypatch, capsys):
    with pytest.raises(SystemExit) as error:
        invoke(["--help"], monkeypatch)

    assert error.value.code == 0
    help_text = capsys.readouterr().out
    assert "Document Converter" in help_text
    assert "dc INPUT.pdf" in help_text


def test_입력과_출력경로가_같으면_변환하지않는다(pdf_file, monkeypatch):
    monkeypatch.setattr("document_convert.cli.convert", lambda *args, **kwargs: pytest.fail("변환하면 안 됨"))

    assert invoke([str(pdf_file), "-o", str(pdf_file)], monkeypatch) == 2
