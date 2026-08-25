#!/usr/bin/env python3
"""Fail CI if private source material is accidentally added."""

import os
from pathlib import Path

from document_convert.privacy import PrivacyViolation, scan_repository


if __name__ == '__main__':
    try:
        raw_terms = os.environ.get('DOCUMENT_CONVERT_FORBIDDEN_TERMS', '')
        terms = [term.strip() for term in raw_terms.split(',') if term.strip()]
        scan_repository(Path(__file__).resolve().parents[1], forbidden_terms=terms)
    except PrivacyViolation as error:
        raise SystemExit(str(error))
