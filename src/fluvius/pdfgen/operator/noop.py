from fluvius.pdfgen.base import PdfOperator, register


@register("noop")
class NoopOperation(PdfOperator):
    """Do nothing, only combines inputs & options into a tuple"""

    def execute(self, *inputs):
        yield from inputs
        yield self.options
