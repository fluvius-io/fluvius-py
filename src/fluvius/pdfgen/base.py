from fii_pdfgen import logger  # isort: skip

from collections import namedtuple

_PdfAction = namedtuple("PdfAction", "op_key options")


def PdfAction(op_key, **options):
    return _PdfAction(op_key, options)


def process_sign_fields(sign_fields):
    if sign_fields is None:
        return []

    if isinstance(sign_fields, list):
        return sign_fields

    return [
        sign_fields,
    ]


class PdfOperator(object):
    def __init__(self, pipeline, key=None, pages=None, sign_fields=None, **options):
        self._pipeline = pipeline
        self._key = key
        self._options = options
        self._pages = pages
        self._sign_fields = process_sign_fields(sign_fields)

        if isinstance(pipeline, PdfOperator):
            self._parent_op = pipeline
            self._pipeline = self._parent_op.pipeline
        else:
            self._parent_op = None
            self._pipeline = pipeline

    @property
    def key(self):
        return self._key

    @property
    def sign_fields(self):
        return self._sign_fields

    @property
    def pages(self):
        return self._pages

    @property
    def pipeline(self):
        return self._pipeline

    @property
    def parent_op(self):
        return self._parent_op

    @property
    def options(self):
        return self._options

    def validate_inputs(self, *inputs):
        pass

    def _render(self, *inputs):
        self.validate_inputs(*inputs)
        yield from self.execute(*inputs)

    def execute(self, *inputs):
        raise NotImplementedError("PdfOperator.execute")


class TemplateSelectorMixin(object):
    def setup_template(self, template):
        """
        @TODO: Quick hack, allow overriding sign_fields and number of pages at template selection
        """  # noqa: E501

        def _template_selector(data):
            if callable(template):
                tmpl = template(data)
            elif isinstance(template, (str, tuple)):
                tmpl = template
            else:
                raise ValueError("Template selector is invalid: %s" % str(template))

            if isinstance(tmpl, tuple):
                tmpl, pages, sign_fields = tmpl
                self._sign_fields = process_sign_fields(sign_fields)
                self._pages = pages or self._pages

            return tmpl

        self._template_selector = _template_selector

    def prepare_data(self, inputs):
        data = {}
        for item in inputs:
            if item is None:
                continue

            data.update(item)

        if callable(self._data_mapper):
            data = dict(self._data_mapper(data))

        if isinstance(self._data_mapper, dict):
            data = {k: data.get(v) for k, v in self._data_mapper.items()}

        if not data:
            return None

        return data


class PdfOperatorsMixin(object):
    def process_ops(self, stages):
        for item in stages:
            if isinstance(item, _PdfAction):
                op = get_op(item.op_key)
                yield op(pipeline=self, **item.options)
                continue

            if isinstance(item, str):
                op = get_op("raw-pdf")
                yield op(self, pdf_file=item)
                continue

            if isinstance(item, (list, tuple)):
                op = get_op("concurrent")
                yield op(self, actions=item)
                continue

            raise ValueError(f"Unsupported pdf operator: {item}")


def __closure__():
    PDF_OPERATION_REGISTRY = {}

    def _register(key, **options):
        def _decorator(cls):
            if key in PDF_OPERATION_REGISTRY:
                raise ValueError("Operation is already registered.")

            if not issubclass(cls, PdfOperator):
                raise ValueError("Operation must be a subclass of PdfOperator")

            PDF_OPERATION_REGISTRY[key] = cls
            logger.info("Registered PDF Operation: %s" % key)
            return cls

        return _decorator

    return PDF_OPERATION_REGISTRY.__getitem__, _register


get_op, register = __closure__()
