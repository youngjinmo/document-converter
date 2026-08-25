#!/usr/bin/env python3
"""Generate synthetic PDFs for local or CI smoke tests."""

from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont


_NOTO_FONT = Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
_KOREAN_TEXT = '테스트 문서'


def _font() -> ImageFont.ImageFont:
    if _NOTO_FONT.is_file():
        return ImageFont.truetype(str(_NOTO_FONT), 42)
    return ImageFont.load_default()


def _insert_text(page: fitz.Page, english: str, korean: str) -> None:
    page.insert_text((72, 72), english)
    if _NOTO_FONT.is_file():
        page.insert_text((72, 108), korean, fontname='noto', fontfile=str(_NOTO_FONT))


def _text_pdf(path: Path) -> None:
    document = fitz.open()
    page = document.new_page()
    _insert_text(page, 'Synthetic digital document', _KOREAN_TEXT)
    document.save(path)


def _image_page() -> bytes:
    image = Image.new('RGB', (900, 180), 'white')
    ImageDraw.Draw(image).text((30, 25), 'Synthetic scanned document', fill='black', font=_font())
    ImageDraw.Draw(image).text((30, 90), _KOREAN_TEXT, fill='black', font=_font())
    stream = BytesIO()
    image.save(stream, format='PNG')
    document = fitz.open()
    page = document.new_page()
    page.insert_image(page.rect, stream=stream.getvalue())
    return document.tobytes()


def _scanned_pdf(path: Path, mixed: bool) -> None:
    scan = fitz.open(stream=_image_page(), filetype='pdf')
    if mixed:
        document = fitz.open()
        page = document.new_page()
        _insert_text(page, 'Synthetic digital page', _KOREAN_TEXT)
        document.insert_pdf(scan)
    else:
        document = scan
    document.save(path)


def main() -> int:
    directory = Path(sys.argv[1]) if len(sys.argv) == 2 else Path('fixtures')
    directory.mkdir(parents=True, exist_ok=True)
    _text_pdf(directory / 'digital.pdf')
    _scanned_pdf(directory / 'scanned.pdf', mixed=False)
    _scanned_pdf(directory / 'mixed.pdf', mixed=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
