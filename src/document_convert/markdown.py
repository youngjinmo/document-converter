"""Best-effort local PDF-to-Markdown rendering."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

import fitz


def render(source: Path, output: Path, assets: Path) -> bool:
    """Render *source* as Markdown, returning whether image assets were written."""
    document = fitz.open(source)
    has_images = False
    try:
        pages: list[str] = []
        for page_number, page in enumerate(document, start=1):
            page_markdown, page_has_images = _render_page(document, page, page_number, assets)
            pages.append(page_markdown)
            has_images = has_images or page_has_images
        output.write_text('\n\n---\n\n'.join(pages).rstrip() + '\n', encoding='utf-8')
    finally:
        document.close()
    return has_images


def _render_page(document: fitz.Document, page: fitz.Page, page_number: int, assets: Path) -> tuple[str, bool]:
    tables = _tables(page)
    elements = _text_elements(page, tables)
    image_count = 0
    for block in page.get_text('dict', flags=fitz.TEXTFLAGS_DICT).get('blocks', []):
        if block.get('type') != 1:
            continue
        xref = block.get('xref', 0)
        data = block.get('image')
        if xref:
            image = document.extract_image(xref)
            data = image.get('image')
            extension = image.get('ext', 'png').lower()
        elif data:
            extension = block.get('ext', 'png').lower()
        else:
            continue
        image_count += 1
        filename = f'page-{page_number:03d}-image-{image_count:03d}.{extension}'
        assets.mkdir(parents=True, exist_ok=True)
        (assets / filename).write_bytes(data)
        destination = quote(f'{assets.name}/{filename}', safe='/')
        elements.append((block['bbox'][1], block['bbox'][0], f'![{filename.rsplit(".", 1)[0]}]({destination})'))

    for rect, rows in tables:
        elements.append((rect.y0, rect.x0, _table_markdown(rows)))

    elements.sort(key=lambda item: (item[0], item[1]))
    return '\n\n'.join(item[2] for item in elements if item[2]), image_count > 0


def _tables(page: fitz.Page) -> list[tuple[fitz.Rect, list[list[str]]]]:
    try:
        found = page.find_tables()
    except (AttributeError, RuntimeError):
        return []
    tables: list[tuple[fitz.Rect, list[list[str]]]] = []
    for table in found.tables:
        rows = [[_clean_cell(cell) for cell in row] for row in table.extract()]
        if len(rows) >= 2 and len(rows[0]) >= 2:
            tables.append((fitz.Rect(table.bbox), rows))
    return tables


def _text_elements(page: fitz.Page, tables: list[tuple[fitz.Rect, list[list[str]]]]) -> list[tuple[float, float, str]]:
    elements: list[tuple[float, float, str]] = []
    table_rects = [rect for rect, _ in tables]
    for block in page.get_text('dict', flags=fitz.TEXTFLAGS_DICT).get('blocks', []):
        if block.get('type') != 0:
            continue
        for line in block.get('lines', []):
            rect = fitz.Rect(line['bbox'])
            if any(rect.intersects(table_rect) for table_rect in table_rects):
                continue
            text = ''.join(span.get('text', '') for span in line.get('spans', [])).strip()
            if not text:
                continue
            size = max((span.get('size', 0) for span in line.get('spans', [])), default=0)
            indent = rect.x0 - page.rect.x0
            elements.append((rect.y0, rect.x0, _line_markdown(text, size, indent)))
    return elements


def _line_markdown(text: str, size: float, indent: float) -> str:
    if size >= 18:
        return f'# {text}'
    if size >= 15:
        return f'## {text}'
    if text.startswith(('• ', '◦ ', '‣ ')):
        return f'- {text[2:].strip()}'
    if _is_numbered(text):
        return text
    if indent >= 80:
        return f'- {text}'
    return text


def _is_numbered(text: str) -> bool:
    prefix, separator, _ = text.partition('. ')
    return bool(separator and prefix.isdigit())


def _table_markdown(rows: list[list[str]]) -> str:
    width = max(len(row) for row in rows)
    normalized = [row + [''] * (width - len(row)) for row in rows]
    lines = [_table_row(normalized[0]), _table_row(['---'] * width)]
    lines.extend(_table_row(row) for row in normalized[1:])
    return '\n'.join(lines)


def _table_row(row: list[str]) -> str:
    return '| ' + ' | '.join(cell.replace('|', '\\|').replace('\n', '<br>') for cell in row) + ' |'


def _clean_cell(cell: str | None) -> str:
    return ' '.join((cell or '').split())
