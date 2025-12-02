from fluvius.pdfgen.base import PdfOperator, PdfOperatorsMixin, register


@register("concurrent")
class ConcurrentOperation(PdfOperator, PdfOperatorsMixin):
    """Run multiple PDF operations and return a list of results, concurrently"""

    def __init__(self, pipeline, actions=None, key=None, pages=None):
        super().__init__(pipeline, key, pages)
        self._actions = tuple(self.process_ops(actions))

    @property
    def options(self):
        return self._actions

    def execute(self, *inputs):
        for pdfop in self._actions:
            for r in pdfop._render(*inputs):
                if r is None:
                    continue
                yield r
