"""Command-line interface for Document Converter."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .converter import convert
from .errors import ConversionError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='dc',
        usage='dc INPUT.pdf [-o OUTPUT.{docx,md}] [--lang LANG] [--no-ocr] [--overwrite] [--timeout TIMEOUT]',
        description='Document Converter: convert a local PDF to DOCX or Markdown.',
    )
    parser.add_argument('input', type=Path, metavar='INPUT.pdf')
    parser.add_argument('-o', '--output', type=Path, metavar='OUTPUT.{docx,md}')
    parser.add_argument('--lang', default='kor+eng', help='Tesseract languages (default: kor+eng)')
    parser.add_argument('--no-ocr', action='store_true', help='Skip OCR and use the source PDF directly.')
    parser.add_argument('--overwrite', action='store_true', help='Replace an existing output file.')
    parser.add_argument('--timeout', type=int, default=300, help='Per-stage timeout in seconds (default: 300)')
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    source = args.input
    target = args.output or source.with_suffix('.docx')
    if source.suffix.lower() != '.pdf' or not source.is_file():
        print('error: INPUT.pdf must be an existing PDF file.', file=sys.stderr)
        return 2
    if target.suffix.lower() not in {'.docx', '.md'}:
        print('error: OUTPUT must use the .docx or .md extension.', file=sys.stderr)
        return 2
    if source.resolve(strict=False) == target.resolve(strict=False):
        print('error: INPUT.pdf and OUTPUT.docx cannot be the same file.', file=sys.stderr)
        return 2
    if target.exists() and not args.overwrite:
        print('error: Output already exists; use --overwrite to replace it.', file=sys.stderr)
        return 2
    assets = target.with_name(f'{target.stem}_assets')
    if target.suffix.lower() == '.md' and assets.exists() and not args.overwrite:
        print('error: Output assets already exist; use --overwrite to replace them.', file=sys.stderr)
        return 2
    if args.timeout <= 0:
        print('error: --timeout must be greater than zero.', file=sys.stderr)
        return 2
    try:
        convert(source, target, lang=args.lang, no_ocr=args.no_ocr, overwrite=args.overwrite, timeout=args.timeout)
    except ConversionError as error:
        print(f'error: {error}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
