from pathlib import Path


def test배포메타데이터는_document_converter_이름과_dc_진입점만_제공한다():
    metadata = (Path(__file__).parents[1] / 'pyproject.toml').read_text(encoding='utf-8')

    assert "description = 'Document Converter" in metadata or "description = \"Document Converter" in metadata
    assert "dc = 'document_convert.cli:main'" in metadata
    assert 'document-convert = ' not in metadata
