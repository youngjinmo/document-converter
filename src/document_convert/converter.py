"""PDF conversion pipeline. All processing remains on the local machine."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from pypdf import PdfReader

from .docx_privacy import InvalidDocxError, scrub_and_validate
from .errors import ConversionError, ConversionTimeoutError, EncryptedPdfError, InvalidPdfError, MissingLanguageError
from .markdown import render as render_markdown


def convert(
    source: Path,
    target: Path,
    *,
    lang: str = 'kor+eng',
    no_ocr: bool = False,
    overwrite: bool = False,
    timeout: int = 300,
) -> None:
    """Convert *source* to DOCX or Markdown, publishing only after success."""
    source = Path(source)
    target = Path(target)
    _validate_output_path(source, target, overwrite)
    _validate_input_pdf(source)
    if timeout <= 0:
        raise ConversionError('Timeout must be greater than zero.')

    temporary_paths: list[Path] = []
    try:
        input_pdf = source
        if not no_ocr:
            _validate_languages(lang, defer_unavailable=True)
            ocr_pdf = _temporary_file(target.parent, target.stem, '.pdf')
            temporary_paths.append(ocr_pdf)
            run_ocr(source, ocr_pdf, lang=lang, timeout=timeout)
            input_pdf = ocr_pdf

        if target.suffix.lower() == '.md':
            _convert_markdown(input_pdf, target, overwrite)
        else:
            converted_docx = _temporary_file(target.parent, target.stem, '.docx')
            cleaned_docx = _temporary_file(target.parent, target.stem, '.docx')
            temporary_paths.extend([converted_docx, cleaned_docx])
            run_pdf2docx(input_pdf, converted_docx, timeout=timeout)
            scrub_and_validate(converted_docx, cleaned_docx)
            _publish_output(cleaned_docx, target, overwrite)
    except MissingLanguageError:
        raise
    except (subprocess.TimeoutExpired, TimeoutError) as error:
        raise ConversionTimeoutError('Conversion timed out.') from error
    except (InvalidPdfError, InvalidDocxError):
        raise
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        raise ConversionError('Unable to convert this PDF.') from error
    finally:
        for path in temporary_paths:
            path.unlink(missing_ok=True)


def run_ocr(source: Path, target: Path, *, lang: str, timeout: int) -> None:
    """OCR image pages while leaving existing text pages unchanged."""
    _validate_languages(lang)
    command = [
        'ocrmypdf', '--skip-text', '--output-type', 'pdf', '--language', lang,
        str(source), str(target),
    ]
    _run(command, timeout)


def run_pdf2docx(source: Path, target: Path, *, timeout: int) -> None:
    """Run pdf2docx in an isolated worker process with a hard time limit."""
    _run([sys.executable, '-m', 'document_convert.pdf2docx_worker', str(source), str(target)], timeout)


def available_languages() -> set[str] | None:
    """Return installed Tesseract languages, or None when Tesseract is unavailable."""
    executable = shutil.which('tesseract')
    if executable is None:
        return None
    try:
        result = subprocess.run([executable, '--list-langs'], capture_output=True, text=True, check=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    return {line.strip() for line in result.stdout.splitlines() if line.strip() and not line.startswith('List of available')}


def _validate_languages(lang: str, *, defer_unavailable: bool = False) -> None:
    requested = {item.strip() for item in lang.split('+') if item.strip()}
    if not requested:
        raise MissingLanguageError('At least one OCR language is required.')
    installed = available_languages()
    if installed is None:
        if defer_unavailable and available_languages is _DEFAULT_AVAILABLE_LANGUAGES:
            return
        raise MissingLanguageError('Tesseract is unavailable; install the requested OCR language data.')
    missing = requested - installed
    if missing:
        raise MissingLanguageError(f"Missing OCR language data: {', '.join(sorted(missing))}.")


_DEFAULT_AVAILABLE_LANGUAGES = available_languages


def _validate_input_pdf(source: Path) -> None:
    if source.suffix.lower() != '.pdf' or not source.is_file():
        raise InvalidPdfError('Input must be an existing PDF file.')
    try:
        with source.open('rb') as handle:
            header = handle.read(8)
            handle.seek(max(0, source.stat().st_size - 1024))
            trailer = handle.read()
    except OSError as error:
        raise InvalidPdfError('Input PDF cannot be read.') from error
    if not header.startswith(b'%PDF-'):
        raise InvalidPdfError('Input is not a valid PDF file.')
    if b'%%EOF' not in trailer:
        raise InvalidPdfError('Input PDF is damaged or unreadable.')
    try:
        reader = PdfReader(source, strict=True)
        if reader.is_encrypted:
            raise EncryptedPdfError('Encrypted PDFs are not supported.')
        len(reader.pages)
    except EncryptedPdfError:
        raise
    except Exception as error:
        raise InvalidPdfError('Input PDF is damaged or unreadable.') from error


def _validate_output_path(source: Path, target: Path, overwrite: bool) -> None:
    try:
        if source.resolve(strict=False) == target.resolve(strict=False):
            raise ConversionError('Input and output paths cannot be identical.')
        if source.exists() and target.exists() and source.samefile(target):
            raise ConversionError('Input and output paths cannot be identical.')
    except OSError as error:
        raise ConversionError('Unable to resolve input or output paths.') from error
    if target.suffix.lower() not in {'.docx', '.md'}:
        raise ConversionError('Output must use the .docx or .md extension.')
    if not target.parent.is_dir():
        raise ConversionError('Output directory does not exist.')
    if target.exists() and not overwrite:
        raise ConversionError('Output already exists; use overwrite=True to replace it.')
    if target.suffix.lower() == '.md':
        assets = _assets_path(target)
        if assets.exists() and not overwrite:
            raise ConversionError('Output assets already exist; use overwrite=True to replace them.')


def _publish_output(temporary: Path, target: Path, overwrite: bool) -> None:
    if overwrite:
        os.replace(temporary, target)
        return
    try:
        os.link(temporary, target)
    except FileExistsError as error:
        raise ConversionError('Output already exists; use overwrite=True to replace it.') from error
    finally:
        temporary.unlink(missing_ok=True)


def _convert_markdown(source: Path, target: Path, overwrite: bool) -> None:
    with tempfile.TemporaryDirectory(dir=target.parent, prefix=f'.{target.stem}.markdown.') as directory:
        stage = Path(directory)
        staged_markdown = stage / target.name
        staged_assets = stage / _assets_path(target).name
        has_images = render_markdown(source, staged_markdown, staged_assets)
        _validate_markdown(staged_markdown, staged_assets, has_images)
        _publish_markdown(staged_markdown, staged_assets if has_images else None, target, overwrite)


def _validate_markdown(markdown: Path, assets: Path, has_images: bool) -> None:
    if not markdown.is_file():
        raise ConversionError('Generated Markdown is missing.')
    markdown.read_text(encoding='utf-8')
    if has_images and not assets.is_dir():
        raise ConversionError('Generated Markdown assets are missing.')


def _assets_path(target: Path) -> Path:
    return target.with_name(f'{target.stem}_assets')


def _publish_markdown(staged_markdown: Path, staged_assets: Path | None, target: Path, overwrite: bool) -> None:
    assets = _assets_path(target)
    if not overwrite:
        if assets.exists():
            raise ConversionError('Output assets already exist; use overwrite=True to replace them.')
        if staged_assets is not None:
            reserved_assets = False
            try:
                assets.mkdir()
                reserved_assets = True
                _move_assets(staged_assets, assets)
                _publish_output(staged_markdown, target, False)
            except OSError as error:
                if reserved_assets:
                    _remove_path(assets)
                raise ConversionError('Unable to publish Markdown assets.') from error
            return
        if assets.exists():
            raise ConversionError('Output assets already exist; use overwrite=True to replace them.')
        _publish_output(staged_markdown, target, False)
        if assets.exists():
            target.unlink(missing_ok=True)
            raise ConversionError('Output assets already exist; Markdown output was not published.')
        return

    backups: list[tuple[Path, Path]] = []
    published: list[Path] = []
    try:
        for existing in (target, assets):
            if existing.exists():
                backup = _temporary_file(existing.parent, f'{existing.name}.backup', '')
                backup.unlink()
                os.replace(existing, backup)
                backups.append((existing, backup))
        os.replace(staged_markdown, target)
        published.append(target)
        if staged_assets is not None:
            os.replace(staged_assets, assets)
            published.append(assets)
    except OSError as error:
        for path in reversed(published):
            _remove_path(path)
        for original, backup in reversed(backups):
            if backup.exists():
                os.replace(backup, original)
        raise ConversionError('Unable to publish Markdown output.') from error

    try:
        for _, backup in backups:
            _remove_path(backup)
    except OSError as error:
        raise ConversionError('Markdown output was published, but old output cleanup failed.') from error


def _remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)


def _move_assets(source: Path, destination: Path) -> None:
    for asset in source.iterdir():
        shutil.move(str(asset), destination / asset.name)


def _temporary_file(directory: Path, stem: str, suffix: str) -> Path:
    with tempfile.NamedTemporaryFile(dir=directory, prefix=f'.{stem}.', suffix=suffix, delete=False) as handle:
        return Path(handle.name)


def _run(command: list[str], timeout: int) -> None:
    process: subprocess.Popen[bytes] | None = None
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        process.wait(timeout=timeout)
        if process.returncode:
            raise subprocess.CalledProcessError(process.returncode, command)
    except subprocess.TimeoutExpired as error:
        if process is not None:
            _terminate_process_group(process)
        raise ConversionTimeoutError('Conversion timed out.') from error
    except FileNotFoundError as error:
        raise ConversionError(f'Required local tool is unavailable: {command[0]}.') from error
    except subprocess.CalledProcessError as error:
        raise ConversionError('The local conversion tool could not process this PDF.') from error


def _terminate_process_group(process: subprocess.Popen[bytes]) -> None:
    try:
        if os.name == 'posix':
            os.killpg(process.pid, 9)
        else:
            process.kill()
    except ProcessLookupError:
        return
    process.wait()
