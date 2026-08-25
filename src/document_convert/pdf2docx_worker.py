"""Small subprocess boundary around pdf2docx."""

from __future__ import annotations

import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    arguments = argv if argv is not None else sys.argv[1:]
    if len(arguments) != 2:
        return 2
    from pdf2docx import Converter

    source, target = (Path(value) for value in arguments)
    converter = Converter(str(source))
    try:
        converter.convert(str(target))
    finally:
        converter.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
