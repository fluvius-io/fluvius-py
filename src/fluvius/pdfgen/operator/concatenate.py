import os
import tempfile

import pypdftk

from fii_pdfgen.base import PdfOperator, register
from fii_pdfgen.datadef import PDFEntry


@register("concatenate")
@register("concat-pdftk")
class PdftkConcatOperation(PdfOperator):
    """Concatenate with fixtures, fixture must have weight"""

    def __init__(self, pipeline, key=None, sign_fields=None):
        key = key or pipeline.template_id
        self._filename = f"{key}.pdf"
        super().__init__(pipeline, key, sign_fields=sign_fields)

    @property
    def options(self):
        return self._fixtures

    def execute(self, *inputs):
        pdf_file = os.path.join(tempfile.mkdtemp(), self._filename)

        files = []
        total_pages = 0
        start_page = 1
        sections = []
        sign_fields = []

        for pdf in inputs:
            if pdf is None:
                continue

            files.append(pdf.file)
            section = pdf.serialize()
            section["offset"] = start_page
            sections.append(section)
            # Compute new sign fields based on declared sign position + offsets
            sign_fields.extend(
                [sf.set(page=sf.page + total_pages) for sf in pdf.sign_fields]
            )
            """
            Using pdftk to get number of pages if we don't define
            number of pages of template, tradeoff is pypdftk will
            cost more time to get number pages.
            Elapse time:
              0.3*10-7 (seconds) (fixed pages)
              0.3 (seconds) (pypdftk)
            """
            pdf_pages = pdf.pages or pypdftk.get_num_pages(pdf.file)
            total_pages += pdf_pages
            start_page += pdf_pages

        out_file = pypdftk.concat(files, out_file=pdf_file)
        yield PDFEntry.create(
            {
                "key": self.key,
                "file": out_file,
                "pages": total_pages,
                "sections": sections,
                "sign_fields": sign_fields,
            }
        )


@register("naive-concatenate")
class PyPDF2ConcatOperation(PdfOperator):
    """Concatenate with fixtures, fixture must have weight"""

    def __init__(self, pipeline, fixtures=tuple()):
        super().__init__(pipeline)
        self._fixtures = tuple((float(idx), pdf) for idx, pdf in fixtures)

    @property
    def options(self):
        return self._fixtures

    def execute(self, *inputs):
        yield tuple(d for k, d in sorted(self._fixtures + tuple(enumerate(inputs))))
