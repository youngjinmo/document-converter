"""Public conversion error types."""


class ConversionError(Exception):
    """The input could not be converted safely."""


class InvalidPdfError(ConversionError):
    """The input is not a readable, unencrypted PDF."""


class EncryptedPdfError(InvalidPdfError):
    """The input PDF requires a password."""


class MissingLanguageError(ConversionError):
    """A requested Tesseract OCR language is unavailable."""


class ConversionTimeoutError(ConversionError):
    """A conversion subprocess exceeded its time limit."""
