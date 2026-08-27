from pathlib import Path
import re


def test배포메타데이터는_document_converter_이름과_dc_진입점만_제공한다():
    metadata = (Path(__file__).parents[1] / 'pyproject.toml').read_text(encoding='utf-8')

    assert "description = 'Document Converter" in metadata or "description = \"Document Converter" in metadata
    assert "dc = 'document_convert.cli:main'" in metadata
    assert 'document-convert = ' not in metadata


def test_ocrmypdf는_pyproject와_requirements에서_호환버전으로고정된다():
    # Given: 배포 메타데이터와 직접 의존성 목록을 읽는다.
    repository = Path(__file__).parents[1]
    metadata = (repository / 'pyproject.toml').read_text(encoding='utf-8')
    requirements = (repository / 'requirements.txt').read_text(encoding='utf-8')

    # When: OCR 선택 의존성과 requirements의 OCRmyPDF 고정을 확인하면
    # Then: 둘 다 최소 호환 버전 16.11.0이어야 한다.
    assert "ocr = ['ocrmypdf==16.11.0']" in metadata
    assert 'ocrmypdf==16.11.0' in requirements.splitlines()


def test_ocr_잠금파일은_호환되는_직접_전이의존성을_고정한다():
    # Given: Python 3.12 Linux 환경용 잠금 의존성 목록을 읽는다.
    lock = (Path(__file__).parents[1] / 'requirements.lock').read_text(encoding='utf-8')

    # When: OCRmyPDF와 pikepdf 및 pi-heif 항목을 확인하면
    # Then: 호환 버전과 정확한 pi-heif 핀이 모두 있어야 한다.
    assert 'ocrmypdf==16.11.0' in lock.splitlines()
    assert 'pikepdf==10.12.0' in lock.splitlines()
    assert any(re.fullmatch(r'pi-heif==[^\s]+', line) for line in lock.splitlines())
