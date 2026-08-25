"""Repository privacy checks for release automation."""

from __future__ import annotations

import re
from pathlib import Path


class PrivacyViolation(ValueError):
    """A repository file includes prohibited personal data or an artifact."""


_EMAIL = re.compile(r'(?<![\w.-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])')
_ARTIFACT = re.compile(r'\.(?:pdf|docx|png|jpe?g|tiff?|webp|zip)$|(?:^|_)ocr\.tsv$|page\d+_ocr\.tsv$', re.I)
_IGNORED_PARTS = {'.git', '.venv', '__pycache__', '.pytest_cache'}
_TEXT_SUFFIXES = {'.py', '.md', '.toml', '.txt', '.lock', '.yml', '.yaml', '.sh', '.json'}
_TEXT_FILENAMES = {'.gitignore', '.dockerignore', 'dockerfile', 'license'}
def scan_repository(root: Path, forbidden_terms: list[str] | None = None) -> list[Path]:
    """Raise on a real email, a forbidden term, or a private generated artifact."""
    root = Path(root)
    terms = [term.lower() for term in forbidden_terms] if forbidden_terms is not None else []
    violations: list[str] = []
    for path in root.rglob('*'):
        if any(part in _IGNORED_PARTS or part.endswith('.egg-info') for part in path.parts) or not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if _ARTIFACT.search(relative):
            violations.append(f'artifact: {relative}')
            continue
        if path.suffix.lower() not in _TEXT_SUFFIXES and path.name.lower() not in _TEXT_FILENAMES:
            violations.append(f'binary file: {relative}')
            continue
        if _is_binary(path):
            violations.append(f'binary file: {relative}')
            continue
        text = path.read_text(encoding='utf-8', errors='ignore')
        found_term = next((term for term in terms if term in text.lower() or term in relative.lower()), None)
        if found_term:
            violations.append(f'forbidden term: {relative}')
            continue
        email = next(
            (item.group(0) for item in _EMAIL.finditer(text) if not _is_placeholder_email(item.group(0), relative)),
            None,
        )
        if email:
            violations.append(f'email: {relative}')
    if violations:
        raise PrivacyViolation('Privacy scan failed: ' + '; '.join(violations))
    return []


def _is_binary(path: Path) -> bool:
    try:
        return b'\0' in path.read_bytes()[:2048]
    except OSError:
        return True


def _is_placeholder_email(value: str, relative: str) -> bool:
    if relative.startswith('tests/') and value.lower().endswith('@example.com'):
        return True
    return value.lower() in {'input@example.com', 'user@example.com', 'name@example.com'}

