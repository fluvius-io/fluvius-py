import os  # noqa: F401
from pathlib import Path

from fii_pdfgen.base import PdfOperator, register
from fii_pdfgen.datadef import PDFEntry


@register("raw-pdf")
class RawPdfOperator(PdfOperator):
    """Fix paths and return a pdf"""

    def __init__(self, pipeline, pdf_file, key=None, pages=None, sign_fields=None):
        super().__init__(pipeline, key, pages, sign_fields=sign_fields)
        self._pdf_file = pdf_file
        self._pages = pages
        if not Path(pdf_file).is_file():
            raise ValueError(f"PDF file does not exists: {pdf_file}")

    def execute(self, *inputs):
        yield PDFEntry.create(
            {
                "key": self.key,
                "file": self._pdf_file,
                "pages": self.pages,
                "sign_fields": self.sign_fields,
            }
        )
