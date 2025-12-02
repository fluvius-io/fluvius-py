""" We could use pypdftk or pdfrw or pypdf2 """

import os
import tempfile

import pypdftk

from fii_pdfgen.base import PdfOperator, TemplateSelectorMixin, register
from fii_pdfgen.datadef import PDFEntry


@register("fill-form")
@register("fill-form-pdftk")
class PdftkFillFormOperation(PdfOperator, TemplateSelectorMixin):
    """Concatenate with fixtures, fixture must have weight"""

    def __init__(
        self,
        pipeline,
        template,
        data_mapper=None,
        key=None,
        pages=None,
        sign_fields=None,
    ):
        super().__init__(pipeline, key, pages, sign_fields=sign_fields)
        self._filename = f"{self.pipeline.template_id}.pdf"
        self._data_mapper = data_mapper
        self.setup_template(template)

    @property
    def options(self):
        return self._fixtures

    def execute(self, *inputs):
        data = self.prepare_data(inputs)
        if data is None:
            return None

        pdf_template = self._template_selector(data)
        if pdf_template is None:
            return None

        pdf_file = os.path.join(tempfile.mkdtemp(), self._filename)
        yield PDFEntry.create(
            {
                "key": self.key,
                "file": pypdftk.fill_form(pdf_template, data, out_file=pdf_file),
                "pages": self.pages,
                "sign_fields": self.sign_fields,
            }
        )
