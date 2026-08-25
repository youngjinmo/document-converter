#!/usr/bin/env python3
"""Validate DOCX package structure and expected WordprocessingML text."""

from __future__ import annotations

import argparse
from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from document_convert.docx_privacy import InvalidDocxError


def validate_docx(path: Path, expected_text: list[str] | None = None) -> None:
    """Raise ``InvalidDocxError`` unless *path* is valid and contains each string."""
    path = Path(path)
    expected_text = expected_text or []
    try:
        with ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise InvalidDocxError('DOCX package is corrupt.')
            names = archive.namelist()
            if '[Content_Types].xml' not in names or 'word/document.xml' not in names:
                raise InvalidDocxError('File is not a DOCX document.')
            text = _word_xml_text(archive, names)
    except (BadZipFile, OSError, ElementTree.ParseError) as error:
        raise InvalidDocxError('File is not a valid DOCX package.') from error

    missing = [item for item in expected_text if item not in text]
    if missing:
        raise InvalidDocxError(f"DOCX is missing expected text: {', '.join(missing)}")


def _word_xml_text(archive: ZipFile, names: list[str]) -> str:
    fragments: list[str] = []
    for name in names:
        if not name.startswith('word/') or not name.endswith('.xml'):
            continue
        root = ElementTree.fromstring(archive.read(name))
        fragments.extend(value for value in root.itertext() if value)
    return ''.join(fragments)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Validate a DOCX package.')
    parser.add_argument('document', type=Path)
    parser.add_argument('--contains', action='append', default=[], help='Expected editable text; may be repeated.')
    args = parser.parse_args(argv)
    try:
        validate_docx(args.document, args.contains)
    except InvalidDocxError as error:
        parser.error(str(error))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
