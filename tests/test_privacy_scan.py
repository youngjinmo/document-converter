from pathlib import Path

import pytest


def test_추적파일과_텍스트에서_금지된_개인정보를_찾는다(tmp_path: Path):
    from document_convert.privacy import PrivacyViolation, scan_repository

    email = "person" + "@" + "example.com"
    (tmp_path / "README.md").write_text("contact " + email, encoding="utf-8")
    with pytest.raises(PrivacyViolation, match="email"):
        scan_repository(tmp_path, forbidden_terms=["private-name"])


def test_허용된_예제도메인과_소스는_통과한다(tmp_path: Path):
    from document_convert.privacy import scan_repository

    (tmp_path / "README.md").write_text("Use input@example.com and example.com", encoding="utf-8")
    assert scan_repository(tmp_path, forbidden_terms=["private-name"]) == []


def test_개인_산출물_파일명은_금지한다(tmp_path: Path):
    from document_convert.privacy import PrivacyViolation, scan_repository

    (tmp_path / "page1_ocr.tsv").write_text("fixture", encoding="utf-8")
    with pytest.raises(PrivacyViolation, match="ocr"):
        scan_repository(tmp_path, forbidden_terms=[])


@pytest.mark.parametrize("filename", ["sample.pdf", "sample.docx", "ocr.tsv", "page99_ocr.tsv"])
def test_개인정보가능_산출물확장자는_파일명과_무관하게_금지한다(tmp_path: Path, filename: str):
    from document_convert.privacy import PrivacyViolation, scan_repository

    (tmp_path / filename).write_bytes(b"synthetic fixture")
    with pytest.raises(PrivacyViolation):
        scan_repository(tmp_path, forbidden_terms=[])


@pytest.mark.parametrize("filename", ["render.png", "render.jpg"])
def test_렌더링이미지_산출물도_금지한다(tmp_path: Path, filename: str):
    from document_convert.privacy import PrivacyViolation, scan_repository

    (tmp_path / filename).write_bytes(b"synthetic fixture")
    with pytest.raises(PrivacyViolation):
        scan_repository(tmp_path, forbidden_terms=[])


def test_tests디렉터리도_스캔대상이며_예제텍스트는_허용한다(tmp_path: Path):
    from document_convert.privacy import scan_repository

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "fixture.txt").write_text("example.com only", encoding="utf-8")
    assert scan_repository(tmp_path, forbidden_terms=["private-name"]) == []


def test_금지된_합성식별자를_차단한다(tmp_path: Path):
    from document_convert.privacy import PrivacyViolation, scan_repository

    (tmp_path / "README.md").write_text("private-name", encoding="utf-8")
    with pytest.raises(PrivacyViolation):
        scan_repository(tmp_path, forbidden_terms=["private-name"])


@pytest.mark.parametrize("suffix", ["_document", "-profile", "의_이력서"])
def test_금지된_합성식별자의_변형문맥도_차단한다(tmp_path: Path, suffix: str):
    from document_convert.privacy import PrivacyViolation, scan_repository

    (tmp_path / "README.md").write_text("prefix-private-name" + suffix, encoding="utf-8")
    with pytest.raises(PrivacyViolation):
        scan_repository(tmp_path, forbidden_terms=["private-name"])


@pytest.mark.parametrize("filename", ["image.webp", "archive.zip"])
def test_허용목록에_없는_바이너리산출물을_차단한다(tmp_path: Path, filename: str):
    from document_convert.privacy import PrivacyViolation, scan_repository

    (tmp_path / filename).write_bytes(b"synthetic binary")
    with pytest.raises(PrivacyViolation):
        scan_repository(tmp_path)


def test_fixture생성기는_이미지페이지를_유효한_pdf로_만든다():
    import importlib.util
    import fitz
    import pytest

    script = Path(__file__).parents[1] / "scripts" / "create_fixtures.py"
    if not script.exists():
        pytest.skip("fixture generator is not present yet")
    spec = importlib.util.spec_from_file_location("create_fixtures", script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    if not hasattr(module, "_image_page"):
        pytest.skip("fixture generator has no _image_page helper")
    pdf = module._image_page()
    document = fitz.open(stream=pdf, filetype="pdf")
    assert document.page_count >= 1
    document.close()
