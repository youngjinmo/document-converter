# Document Converter

[English](README.md) | [한국어](README.ko.md) | [简体中文](README.zh-CN.md)

Convert a local PDF into an editable DOCX or Markdown file with optional Korean and English OCR.
Documents never leave your computer and their text is never logged.

## License notice before installation

This repository's code is MIT licensed. The conversion dependency chain uses
PyMuPDF through `pdf2docx`; PyMuPDF is AGPL-licensed unless you obtain its
commercial license. Review [PyMuPDF licensing](https://github.com/pymupdf/PyMuPDF)
before redistributing a combined application. Details are in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Quick start with Docker

Docker is the recommended option because it includes Tesseract, Korean/English
language data, and CJK fonts.

```sh
git clone <repository-url> document-convert
cd document-convert
./run.sh input.pdf output.md
```

The input directory is mounted read-only. Only the output directory is writable
inside the container.

## CLI

```sh
dc INPUT.pdf [-o OUTPUT.docx|OUTPUT.md]
```

Options:

- `--lang kor+eng` sets OCR languages (the default is `kor+eng`).
- `--no-ocr` skips OCR for PDFs that already have reliable text.
- `--overwrite` replaces an existing output file (and Markdown assets directory).
- `--timeout 300` sets the per-stage time limit in seconds.

The conversion first runs OCRmyPDF with `--skip-text`, preserving text pages.
DOCX output then runs through `pdf2docx` and is checked as OOXML with author,
title, company, and custom document properties cleared. Markdown output uses
local PyMuPDF text, table, and image extraction; images are written beside the
document in `<output>_assets/` and linked with relative paths.

## Run without Docker

Install Python 3.11+ and Tesseract with Korean and English language data, then:

```sh
python -m venv .venv
. .venv/bin/activate
pip install -e '.[ocr]'
dc input.pdf -o output.docx
```

- macOS: `brew install tesseract tesseract-lang`
- Ubuntu/WSL: `sudo apt install tesseract-ocr tesseract-ocr-kor tesseract-ocr-eng ghostscript qpdf`
- Windows: install Tesseract with `kor` and `eng` data and Ghostscript, then
  add both installation directories to `PATH`. Use PowerShell to activate the
  virtual environment and run the same `pip`/CLI commands.

For other languages, install the corresponding Tesseract `traineddata` file
and pass its language code with `--lang`, for example `--lang deu+eng`.

## Limitations and troubleshooting

PDF is a fixed-layout format. Complex columns, unusual fonts, tables, shapes,
and handwriting may need manual DOCX cleanup. OCR quality depends on scan
resolution and source language. Use `--no-ocr` for clean digital PDFs.

If conversion reports a missing language, install its Tesseract language data.
If it times out, use a smaller PDF, increase `--timeout`, or use Docker to
ensure local dependencies are available. Password-protected or damaged PDFs
are rejected without modifying an existing output file.

`requirements.lock` contains fully pinned transitive constraints captured for
the Python 3.12 Linux Docker target. It is not hash-locked or cross-platform:
native wheels differ by operating system and Python version. Use Docker for the
most repeatable runtime.
The requested newer `pdf2docx`, PyMuPDF, and OCRmyPDF versions were not
available from the configured package index, so the lock uses the newest
resolvable releases from that index instead; PyMuPDF is pinned to the
empirically compatible `1.25.5` release.

The CI Docker smoke test generates synthetic digital, scanned, and mixed PDFs
and verifies that both English and Korean text remain editable in each DOCX.
