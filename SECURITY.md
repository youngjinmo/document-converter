# Security and privacy

Do not report sensitive documents in a public issue. For a potential security
or privacy issue, contact the maintainers through the repository's private
security-advisory channel and include only a synthetic reproduction.

The tool processes files locally. Review generated DOCX files before sharing:
OCR and conversion cannot guarantee removal of content already present in the
source PDF.

Before making the repository public, configure the
`DOCUMENT_CONVERT_FORBIDDEN_TERMS` repository secret with a comma-separated
private denylist. Do not place those values in source, issues, or pull requests.
Fork pull requests cannot access repository secrets; generic email, binary, and
artifact checks remain active for them.
