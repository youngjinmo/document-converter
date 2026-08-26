from pathlib import Path

import pytest


def _make_markdown_pdf(path: Path) -> None:
    fitz = pytest.importorskip('fitz')
    document = fitz.open()

    first = document.new_page(width=612, height=792)
    first.insert_text((72, 72), '문서 제목 / Document title', fontsize=20, fontname='korea')
    first.insert_text((72, 112), '첫 번째 문단입니다. This is the first paragraph.', fontsize=12, fontname='korea')
    first.insert_text((84, 150), '첫 번째 항목', fontsize=12, fontname='korea')
    first.insert_text((84, 170), '두 번째 항목', fontsize=12, fontname='korea')
    first.insert_text((84, 190), '세 번째 항목', fontsize=12, fontname='korea')
    first.draw_rect(fitz.Rect(72, 230, 300, 290), color=(0, 0, 0), width=1)
    first.draw_line((186, 230), (186, 290), color=(0, 0, 0), width=1)
    first.draw_line((72, 260), (300, 260), color=(0, 0, 0), width=1)
    first.insert_text((82, 250), '이름', fontsize=11, fontname='korea')
    first.insert_text((196, 250), '값', fontsize=11, fontname='korea')
    first.insert_text((82, 280), '한글', fontsize=11, fontname='korea')
    first.insert_text((196, 280), 'English', fontsize=11, fontname='korea')

    second = document.new_page(width=612, height=792)
    second.insert_text((72, 72), '두 번째 페이지', fontsize=16, fontname='korea')
    document.save(path)
    document.close()


def _make_image_pdf(path: Path) -> None:
    fitz = pytest.importorskip('fitz')
    document = fitz.open()
    page = document.new_page(width=612, height=792)
    page.insert_text((72, 72), '앞 텍스트', fontsize=12, fontname='korea')
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 16, 16), False)
    pixmap.clear_with(255)
    page.insert_image(fitz.Rect(72, 100, 144, 172), pixmap=pixmap)
    page.insert_text((72, 200), '뒤 텍스트', fontsize=12, fontname='korea')
    document.save(path)
    document.close()


def test_pdf를_markdown으로_변환하면_제목_문단_목록_표와_페이지구분을_보존한다(tmp_path):
    from document_convert.converter import convert

    source = tmp_path / 'formatted.pdf'
    target = tmp_path / 'formatted.md'
    _make_markdown_pdf(source)

    convert(source, target, no_ocr=True)

    markdown = target.read_text(encoding='utf-8')
    assert '# 문서 제목 / Document title' in markdown
    assert '첫 번째 문단입니다. This is the first paragraph.' in markdown
    assert '- 첫 번째 항목' in markdown
    assert '- 두 번째 항목' in markdown
    assert '| 이름 | 값 |' in markdown
    assert '| --- | --- |' in markdown
    assert '| 한글 | English |' in markdown
    assert '\n---\n' in markdown


def test_pdf의_이미지는_assets에_페이지와_순서가_포함된_이름으로_저장되고_상대링크가_삽입된다(tmp_path):
    from document_convert.converter import convert

    source = tmp_path / 'images.pdf'
    target = tmp_path / 'report.md'
    _make_image_pdf(source)

    convert(source, target, no_ocr=True)

    assets = target.parent / 'report_assets'
    image = assets / 'page-001-image-001.png'
    assert image.exists()
    assert image.read_bytes().startswith(b'\x89PNG')
    markdown = target.read_text(encoding='utf-8')
    assert '![page-001-image-001](report_assets/page-001-image-001.png)' in markdown
    assert markdown.index('앞 텍스트') < markdown.index('report_assets/page-001-image-001.png') < markdown.index('뒤 텍스트')


def test_이미지가_없는_pdf는_assets_디렉터리를_만들지_않는다(tmp_path):
    from document_convert.converter import convert

    source = tmp_path / 'text.pdf'
    target = tmp_path / 'text.md'
    _make_markdown_pdf(source)
    # The fixture has no embedded raster image, so only the text output is expected.
    convert(source, target, no_ocr=True)

    assert target.exists()
    assert not (tmp_path / 'text_assets').exists()


def test_markdown과_assets가_이미_있으면_overwrite_없이_실패하고_기존결과를_보존한다(tmp_path):
    from document_convert.converter import ConversionError, convert

    source = tmp_path / 'input.pdf'
    target = tmp_path / 'result.md'
    assets = tmp_path / 'result_assets'
    _make_markdown_pdf(source)
    target.write_text('old markdown', encoding='utf-8')
    assets.mkdir()
    (assets / 'old.txt').write_text('old asset', encoding='utf-8')

    with pytest.raises(ConversionError, match='exist|overwrite'):
        convert(source, target, no_ocr=True)

    assert target.read_text(encoding='utf-8') == 'old markdown'
    assert (assets / 'old.txt').read_text(encoding='utf-8') == 'old asset'


def test_overwrite는_markdown과_assets를_함께_교체한다(tmp_path):
    from document_convert.converter import convert

    source = tmp_path / 'input.pdf'
    target = tmp_path / 'result.md'
    assets = tmp_path / 'result_assets'
    _make_image_pdf(source)
    target.write_text('old markdown', encoding='utf-8')
    assets.mkdir()
    (assets / 'old.txt').write_text('old asset', encoding='utf-8')

    convert(source, target, no_ocr=True, overwrite=True)

    assert 'old markdown' not in target.read_text(encoding='utf-8')
    assert not (assets / 'old.txt').exists()
    assert (assets / 'page-001-image-001.png').exists()


def test_overwrite_중_변환실패시_markdown과_assets를_보존한다(tmp_path):
    from document_convert.converter import ConversionError, convert

    source = tmp_path / 'broken.pdf'
    target = tmp_path / 'result.md'
    assets = tmp_path / 'result_assets'
    source.write_bytes(b'%PDF-1.7\nnot a valid document\n%%EOF\n')
    target.write_text('old markdown', encoding='utf-8')
    assets.mkdir()
    (assets / 'old.txt').write_text('old asset', encoding='utf-8')

    with pytest.raises(ConversionError):
        convert(source, target, no_ocr=True, overwrite=True)

    assert target.read_text(encoding='utf-8') == 'old markdown'
    assert (assets / 'old.txt').read_text(encoding='utf-8') == 'old asset'


@pytest.mark.parametrize('failure_at', [1, 2, 3, 4])
def test_overwrite_게시중_os_replace_실패해도_기존_markdown과_assets를_보존한다(tmp_path, monkeypatch, failure_at):
    from document_convert.converter import ConversionError, convert
    import document_convert.converter as converter

    source = tmp_path / 'input.pdf'
    target = tmp_path / 'result.md'
    assets = tmp_path / 'result_assets'
    _make_image_pdf(source)
    target.write_text('old markdown', encoding='utf-8')
    assets.mkdir()
    (assets / 'old.txt').write_text('old asset', encoding='utf-8')
    original_replace = converter.os.replace
    calls = {'count': 0}

    def fail_once_at(path, destination):
        calls['count'] += 1
        if calls['count'] == failure_at:
            raise OSError('injected publish failure')
        return original_replace(path, destination)

    monkeypatch.setattr(converter.os, 'replace', fail_once_at)
    with pytest.raises(ConversionError):
        convert(source, target, no_ocr=True, overwrite=True)

    assert target.read_text(encoding='utf-8') == 'old markdown'
    assert (assets / 'old.txt').read_text(encoding='utf-8') == 'old asset'


def test_markdown_게시후_정리실패가_새_결과를_삭제하지_않는다(tmp_path, monkeypatch):
    from document_convert.converter import ConversionError, convert
    import document_convert.converter as converter

    source = tmp_path / 'input.pdf'
    target = tmp_path / 'result.md'
    assets = tmp_path / 'result_assets'
    _make_image_pdf(source)
    target.write_text('old markdown', encoding='utf-8')
    assets.mkdir()
    (assets / 'old.txt').write_text('old asset', encoding='utf-8')
    original_remove = converter._remove_path
    calls = {'count': 0}

    def fail_cleanup(path):
        calls['count'] += 1
        if calls['count'] == 1:
            raise OSError('injected cleanup failure')
        return original_remove(path)

    monkeypatch.setattr(converter, '_remove_path', fail_cleanup)
    with pytest.raises(ConversionError):
        convert(source, target, no_ocr=True, overwrite=True)

    assert 'old markdown' not in target.read_text(encoding='utf-8')
    assert (assets / 'page-001-image-001.png').exists()


def test_빈_assets가_게시직전에_생겨도_markdown을_남기지_않고_디렉터리를_보존한다(tmp_path, monkeypatch):
    from document_convert.converter import ConversionError, convert

    source = tmp_path / 'input.pdf'
    target = tmp_path / 'result.md'
    assets = tmp_path / 'result_assets'
    _make_image_pdf(source)

    original_mkdir = Path.mkdir

    def race_create_assets(path, *args, **kwargs):
        if path == assets:
            original_mkdir(path)
            raise FileExistsError(path)
        return original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'mkdir', race_create_assets)
    with pytest.raises(ConversionError):
        convert(source, target, no_ocr=True)

    assert not target.exists()
    assert assets.is_dir()
    assert not list(assets.iterdir())


def test_공백이_있는_markdown_출력은_유효한_GFM_이미지_destination을_생성한다(tmp_path):
    from document_convert.converter import convert

    source = tmp_path / 'input.pdf'
    target = tmp_path / 'my report.md'
    _make_image_pdf(source)

    convert(source, target, no_ocr=True)

    markdown = target.read_text(encoding='utf-8')
    assert (
        '(my%20report_assets/page-001-image-001.png)' in markdown
        or '(<my report_assets/page-001-image-001.png>)' in markdown
    )
