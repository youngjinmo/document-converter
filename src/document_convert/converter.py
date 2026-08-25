"""PDF-to-DOCX conversion pipeline. All processing remains on the local machine."""

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


def convert(
    source: Path,
    target: Path,
    *,
    lang: str = 'kor+eng',
    no_ocr: bool = False,
    overwrite: bool = False,
    timeout: int = 300,
) -> None:
    """Convert *source* to *target*, replacing the target only after success."""
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
    if target.suffix.lower() != '.docx':
        raise ConversionError('Output must use the .docx extension.')
    if not target.parent.is_dir():
        raise ConversionError('Output directory does not exist.')
    if target.exists() and not overwrite:
        raise ConversionError('Output already exists; use overwrite=True to replace it.')


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
