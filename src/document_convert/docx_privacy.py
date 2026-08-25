"""Remove document properties that may identify the document creator."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile

class InvalidDocxError(ValueError):
    """Raised when a DOCX package is corrupt or cannot be read."""


def scrub_and_validate(source: Path, target: Path) -> None:
    """Write a valid DOCX with core, app, and custom properties cleared."""
    source = Path(source)
    target = Path(target)
    try:
        with ZipFile(source) as archive:
            if archive.testzip() is not None:
                raise InvalidDocxError('Generated DOCX is corrupt.')
    except (BadZipFile, OSError) as error:
        raise InvalidDocxError('Generated file is not a valid DOCX package.') from error

    try:
        with tempfile.NamedTemporaryFile(
            dir=target.parent, prefix=f'.{target.stem}.', suffix='.docx', delete=False
        ) as handle:
            temporary = Path(handle.name)
        try:
            _copy_package(source, temporary)
            _clear_package_properties(temporary)
            _validate_docx(temporary)
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    except InvalidDocxError:
        raise
    except (BadZipFile, OSError, ValueError) as error:
        raise InvalidDocxError('Generated file is not a valid DOCX package.') from error


def _clear_package_properties(path: Path) -> None:
    """Clear values in app/custom property XML without changing package layout."""
    with ZipFile(path, 'r') as source:
        contents = {info.filename: source.read(info.filename) for info in source.infolist()}

    custom_properties_present = 'docProps/custom.xml' in contents
    contents.pop('docProps/custom.xml', None)
    core_xml = contents.get('docProps/core.xml')
    if core_xml:
        contents['docProps/core.xml'] = _clear_core_properties(core_xml)
    app_xml = contents.get('docProps/app.xml')
    if app_xml:
        contents['docProps/app.xml'] = _clear_xml_text(app_xml, {'Company', 'Manager', 'HyperlinkBase'})
    relationships = contents.get('_rels/.rels')
    if relationships and (custom_properties_present or _contains_custom_property_reference(relationships)):
        contents['_rels/.rels'] = _remove_custom_property_reference(relationships)
    content_types = contents.get('[Content_Types].xml')
    if content_types and (custom_properties_present or _contains_custom_property_reference(content_types)):
        contents['[Content_Types].xml'] = _remove_custom_property_reference(content_types)

    with ZipFile(path, 'w', ZIP_DEFLATED) as target:
        for name, value in contents.items():
            target.writestr(name, value)


def _clear_xml_text(content: bytes, names: set[str] | None) -> bytes:
    from xml.etree import ElementTree

    root = ElementTree.fromstring(content)
    for element in root.iter():
        local_name = element.tag.rsplit('}', 1)[-1]
        if names is None or local_name in names or local_name.startswith('lpwstr'):
            element.text = ''
    return ElementTree.tostring(root, encoding='utf-8', xml_declaration=True)


def _remove_custom_property_reference(content: bytes) -> bytes:
    from xml.etree import ElementTree

    root = ElementTree.fromstring(content)
    for parent in root.iter():
        for child in list(parent):
            if _is_custom_property_reference(child):
                parent.remove(child)
    return ElementTree.tostring(root, encoding='utf-8', xml_declaration=True)


def _contains_custom_property_reference(content: bytes) -> bool:
    from xml.etree import ElementTree

    root = ElementTree.fromstring(content)
    return any(_is_custom_property_reference(element) for element in root.iter())


def _is_custom_property_reference(element: object) -> bool:
    attributes = getattr(element, 'attrib', {})
    values = {value.replace('\\', '/').lstrip('/').lower() for value in attributes.values()}
    return (
        'docprops/custom.xml' in values
        or any('custom-properties' in value for value in values)
    )


def _remove_core_dates(content: bytes) -> bytes:
    from xml.etree import ElementTree

    root = ElementTree.fromstring(content)
    for child in list(root):
        if child.tag.rsplit('}', 1)[-1] in {'created', 'modified', 'lastPrinted'}:
            root.remove(child)
    return ElementTree.tostring(root, encoding='utf-8', xml_declaration=True)


def _clear_core_properties(content: bytes) -> bytes:
    from xml.etree import ElementTree

    identifying_fields = {
        'title', 'subject', 'creator', 'keywords', 'description', 'lastModifiedBy',
        'category', 'identifier',
    }
    root = ElementTree.fromstring(content)
    for child in list(root):
        local_name = child.tag.rsplit('}', 1)[-1]
        if local_name in {'created', 'modified', 'lastPrinted'}:
            root.remove(child)
        elif local_name == 'revision':
            value = (child.text or '').strip()
            child.text = value if value.isdigit() and int(value) > 0 else '1'
        elif local_name in identifying_fields:
            root.remove(child)
    return ElementTree.tostring(root, encoding='utf-8', xml_declaration=True)


def _copy_package(source: Path, target: Path) -> None:
    with ZipFile(source, 'r') as archive, ZipFile(target, 'w', ZIP_DEFLATED) as copied:
        for item in archive.infolist():
            copied.writestr(item, archive.read(item.filename))


def _validate_docx(path: Path) -> None:
    try:
        with ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise InvalidDocxError('Generated DOCX is corrupt.')
            if '[Content_Types].xml' not in archive.namelist() or 'word/document.xml' not in archive.namelist():
                raise InvalidDocxError('Generated file is not a DOCX document.')
    except (BadZipFile, OSError, ValueError) as error:
        raise InvalidDocxError('Generated file is not a valid DOCX package.') from error


def validate_docx(path: Path, expected_text: list[str] | None = None) -> bool:
    """Validate package structure and expected text across all Word XML parts."""
    expected_text = expected_text or []
    try:
        with ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise InvalidDocxError('DOCX package is corrupt.')
            names = archive.namelist()
            if '[Content_Types].xml' not in names or 'word/document.xml' not in names:
                raise InvalidDocxError('File is not a DOCX document.')
            text = _word_xml_text(archive, names)
    except (BadZipFile, OSError, ValueError) as error:
        raise InvalidDocxError('File is not a valid DOCX package.') from error
    missing = [item for item in expected_text if item not in text]
    if missing:
        raise InvalidDocxError(f"DOCX is missing expected text: {', '.join(missing)}")
    return True


def _word_xml_text(archive: ZipFile, names: list[str]) -> str:
    from xml.etree import ElementTree

    fragments: list[str] = []
    for name in names:
        if name.startswith('word/') and name.endswith('.xml'):
            root = ElementTree.fromstring(archive.read(name))
            fragments.extend(value for value in root.itertext() if value)
    return ''.join(fragments)
