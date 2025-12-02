import os
import tempfile
import traceback

import pdfkit

from fii_pdfgen import config
from fii_pdfgen.base import PdfOperator, TemplateSelectorMixin, register
from fii_pdfgen.datadef import PDFEntry
from fii_pdfgen.engine import jinja2renderer


@register("html2pdf")
@register("wkhtml2pdf")
class WkHtml2PdfOperator(PdfOperator, TemplateSelectorMixin):
    """Concatenate with fixtures, fixture must have weight"""

    def __init__(
        self,
        pipeline,
        template=None,
        data_mapper=None,
        key=None,
        sign_fields=None,
        pages=None,
        **options,
    ):
        key = key
        super().__init__(pipeline, key, pages, sign_fields=sign_fields)
        self._filename = f"{self.pipeline.template_id}.pdf"
        self._data_mapper = data_mapper
        self.setup_template(template)
        self.setup_options(options)

    def setup_options(self, opts):
        self._options = {
            "disable-smart-shrinking": "",
            "enable-local-file-access": None,
            "encoding": "UTF-8",
            "footer-font-size": "10",
            "header-font-size": "10",
            "header-right": "[date]",
            "header-spacing": 15,
            "load-error-handling": "ignore",
            "load-media-error-handling": "ignore",
            "margin-bottom": "0.9525cm",
            "margin-left": "0.9525cm",
            "margin-right": "0.9525cm",
            "margin-top": "0.9525cm",
            "page-size": "Letter",
        }
        self._options.update(opts)

    def execute(self, *inputs):
        data = self.prepare_data(inputs)
        if data is None:
            return None

        pdf_file = os.path.join(tempfile.mkdtemp(), self._filename)
        html_template = self._template_selector(data)
        relative_path = os.path.relpath(html_template, config.TEMPLATE_DIR)

        try:
            html = jinja2renderer.render(relative_path, data)
        except Exception as e:
            stack_trace = traceback.format_exc()
            html = f"""
                <html><body>
                <h3>Cannot render document</h3>
                <h4>Template: {html_template}</h4>
                <h4>Error: {str(e)}</h4>
                <code><pre style="font-size: 0.8em">{stack_trace}</pre></code>
                </body></html>"""

        pdfkit.from_string(html, pdf_file, options=self.options)

        yield PDFEntry.create(
            {
                "key": self.key,
                "file": pdf_file,
                "pages": 1,
                "sign_fields": self.sign_fields,
            }
        )
