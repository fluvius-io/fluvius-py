from fluvius.pdfgen import logger
from fluvius.pdfgen.base import PdfOperatorsMixin


def __closure__():
    PDF_PIPELINE_FUNCTION = {}

    def register_pdf_template(template_id, **options):
        def decorator(func):
            if template_id is None:
                return

            if template_id in PDF_PIPELINE_FUNCTION:
                raise ValueError("Template ID is already registered: %s" % template_id)

            PDF_PIPELINE_FUNCTION[template_id] = (func, options, None)
            logger.info(
                "Registered template function [%s] with id [%s]", func, template_id
            )
            return func

        return decorator

    def get_pipeline(template_id):
        if template_id not in PDF_PIPELINE_FUNCTION:
            raise ValueError("Template ID does not exists: [%s]" % template_id)

        func, opts, pipeline = PDF_PIPELINE_FUNCTION[template_id]

        if not pipeline:
            pipeline = PdfPipeline(func(), template_id, **opts)
            PDF_PIPELINE_FUNCTION[template_id] = (func, opts, pipeline)

        return pipeline

    class PdfPipeline(PdfOperatorsMixin):
        """Generic PDF Pipeline"""

        def __init__(self, stages, template_id=None, **options):
            self._template_id = template_id
            self._stages = tuple(self.process_ops(stages))

        @property
        def stages(self):
            return self._stages

        @property
        def template_id(self):
            return self._template_id

        def render(self, *inputs):
            results = inputs
            for pdfop in self.stages:
                results = tuple(pdfop._render(*results))

            return results

        def __repr__(self):
            def gen():
                yield f"PIPELINE: {self.__doc__}"
                for idx, stage in enumerate(self.stages, start=1):
                    yield f"STAGE {idx:2}: {getattr(stage, '__doc__', '[No docstring]')}"  # noqa: E501
                    yield f"  OPTIONS => {stage.options}"

            return "\n".join(gen())

    return PdfPipeline, register_pdf_template, get_pipeline, PDF_PIPELINE_FUNCTION.keys


PdfPipeline, register_pdf_template, get_pipeline, enumerate_pipeline = __closure__()
