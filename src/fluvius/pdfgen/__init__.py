from ._meta import config, logger  # isort: skip
from . import operator  # noqa: F401
from .base import PdfAction
from .datadef import SignField
from .pipeline import PdfPipeline, get_pipeline, register_pdf_template


def genpdf(template_id, *inputs):
    pipeline = get_pipeline(template_id)
    (pdf_file,) = pipeline.render(*inputs)
    return pdf_file


__all__ = (
    "genpdf",
    "register_pdf_template",
    "PdfAction",
    "SignField",
    "PdfPipeline",
    "config",
    "logger",
)
