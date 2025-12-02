import functools
import queue

from fluvius.error import BadRequestError
from fluvius.dmap import logger, config, writer
from fluvius.dmap.interface import OutputRow, DataElement, PipelineConfig, ReaderError, ReaderFinished, ResourceMeta
from fluvius.dmap.typecast import get_coercer_profile, get_dtype, get_reducer
from .transform import process_tfspec


BUILTIN_FIELD_PRID = config.BUILTIN_FIELD_PRID
BUILTIN_FIELD_INDEX = config.BUILTIN_FIELD_INDEX
BUILTIN_FIELD_COUNTER = config.BUILTIN_FIELD_COUNTER
READ_TIMEOUT = config.READ_TIMEOUT


def pipe_compose(*functions):
    def _compose(f, g):
        def composite_coercer(val, obj):
            # NOTE: the order of the function is reversed compared to the input
            # since the pipe is applied from left to right (e.g. float|integer)
            return g(f(val, obj), obj)

        return composite_coercer

    return functools.reduce(_compose, functions)


class ProcessPipeline(object):
    def __init__(self, config):
        self._config = config
        self._transforms = process_tfspec(self.config.transforms)        
        self._transaction_loop = self.config.transaction
        self._input_queue = queue.Queue()

        self._coercer_profile = get_coercer_profile(self.config.coercer_profile)
        self._init_mapping(self.config.mapping)
        self._writer = writer.init_writer(self.config.writer)
        self._writer.setup(self)
        self._counter = 0

    def consume_queue(self, input_conn):
        while True:
            try:
                data = input_conn.get(timeout=READ_TIMEOUT)                

                if isinstance(data, ResourceMeta):
                    self.set_metadata(data)
                    continue

                if isinstance(data, ReaderError):
                    logger.warning('Writer [%s] stopped due to reader error.', self.pipeline_key)
                    break

                if data == ReaderFinished:
                    break

                yield data                
                input_conn.task_done()
            except queue.Empty:
                logger.warning('[%20s] Timeout! %ds. %d record(s) processed.', self.pipeline_key, READ_TIMEOUT, self.counter)
                return

    @property
    def metadata(self):
        return self._metadata

    @property
    def counter(self):
        return self._counter

    @property
    def index(self):
        return self._index

    def counter_incr(self):
        self._counter += 1
        self._index += 1

    @property
    def writer(self):
        return self._writer

    def set_metadata(self, metadata):
        self._metadata = metadata

    @property
    def transaction_loop(self):
        return self._transaction_loop

    @property
    def config(self):
        return self._config

    @property
    def pipeline_key(self):
        return self.config.key

    @property
    def coercer_profile(self):
        return self._coercer_profile

    @property
    def input_queue(self):
        return self._input_queue

    @property
    def transforms(self):
        return self._transforms

    @property
    def context(self):
        return self._context

    @property
    def field_hdr(self):
        return self._field_hdr

    @property
    def field_map(self):
        return self._field_map

    @property
    def field_dtypes(self):
        return self._field_dtypes

    def _init_mapping(self, mapping):

        COERCER_MAP = {}

        def _coercer(spec):
            if not spec:
                return None

            if '|' in spec:
                spec_list = spec.split('|')
                return pipe_compose(*[_coercer(f) for f in spec_list])

            spec = spec.strip()
            if spec in COERCER_MAP:
                return COERCER_MAP[spec]

            COERCER_MAP[spec] = self.coercer_profile.build_coercer(spec)
            return COERCER_MAP[spec]

        def _gen_dtypes(fmap):
            ''' @TODO: This method need to be straitened and write some proper explanation
            '''
            for idx, (output_key, spec) in enumerate(mapping.items()):
                if isinstance(spec, list):
                    reducer = get_reducer('array')
                    for entry in spec:
                        input_key, _, coercer_spec = entry.partition("|")
                        fmap.setdefault(input_key, tuple())
                        coercer = _coercer(coercer_spec)
                        fmap[input_key] += ((idx, output_key, reducer, coercer),)
                elif isinstance(spec, str):
                    input_key, _, coercer_spec = spec.partition("|")

                    if not input_key:
                        input_key = output_key

                    if ':' in input_key:
                        reducer_spec, _, input_key = input_key.partition(':')
                        reducer = get_reducer(reducer_spec)
                    else:
                        reducer = None

                    coercer = _coercer(coercer_spec)
                    fmap.setdefault(input_key, tuple())
                    fmap[input_key] += ((idx, output_key, reducer, coercer), )
                elif isinstance(spec, dict):
                    reducer = get_reducer(spec.get('reducer'))
                    coercer = _coercer(spec.get('coercer'))
                    for input_key in spec['inputs']:
                        fmap.setdefault(input_key, tuple())
                        fmap[input_key] += ((idx, output_key, reducer, coercer), )
                elif not spec:  # Falsy, e.g. empty dict, null, empty string
                    input_key = output_key
                    coercer = None
                    reducer = None
                    fmap.setdefault(input_key, tuple())
                    fmap[input_key] += ((idx, output_key, None, None), )
                else:
                    raise BadRequestError(
                        "T00.401",
                        f"Invalid mapping spec: {spec}",
                        None
                    )

                dtype = get_dtype(reducer) if reducer else get_dtype(coercer)
                yield output_key, dtype  # None is segment id

        fmap = {}
        self._field_dtypes = tuple(_gen_dtypes(fmap))
        self._field_hdr = tuple(output_key for output_key, _ in self.field_dtypes)
        self._field_map = fmap

    def row_collector(self, **meta):
        # yield values from context
        yield BUILTIN_FIELD_INDEX, self.index, None
        yield BUILTIN_FIELD_COUNTER, self.counter, None

        if self.config.allow_ctx_buffer:
            for buff in self.context_buffer.values():
                yield from buff

        for buff in self.row_buffer:
            yield from buff

        for k, v in meta.items():
            yield k, v, None

    def emit_row(self, loop_meta):
        obj = {}
        self.counter_incr()

        for ele_id, ele_val, _ in self.row_collector(**self.metadata, **loop_meta):
            if ele_id not in self.field_map:
                continue

            for idx, key, reducer, coercer in self.field_map[ele_id]:
                if coercer:
                    try:
                        val = coercer(ele_val, obj)
                    except Exception:
                        logger.error(
                            'Error processing entry [%d], element [%s], value [%s] (%s)',
                            self.counter, key, ele_val, coercer.__name__
                        )
                        raise
                else:
                    val = ele_val

                if reducer is not None:
                    obj[key] = reducer(obj.get(key), val, ele_id)
                elif key not in obj:
                    obj[key] = val
                else:
                    raise BadRequestError(
                        "T00.402",
                        f"No reducer specified yet there are multiple values: {key} => {ele_id} : {ele_val} | {obj[key]}",
                        None
                    )

        return OutputRow(obj.get(k) for k in self.field_hdr)

    def ingest_loop(self, data_loop):
        # Descending (i.e. go down), keep track of how deep we get.
        # Reset the row buffer at start of transaction loop
        if data_loop.id == self.transaction_loop:
            self.row_collection = True
            self.row_buffer = []

        # Note: separated ifs since there will be child loops as well
        if self.row_collection:
            self.row_buffer.append(data_loop.elements)
            return

        # Add dataloop into the context buffer
        # @TODO: the context buffer concept may need a serious re-evaluation
        # it works well enough for most of the ansi-x12 cases but if the mapping
        # is wrong, it may leads to incorrectly emitting sub transaction values
        # or missed some context values.
        if data_loop.id is not None:
            self.context_buffer[data_loop.id] = data_loop.elements

    def _consume(self):
        self.row_depth = 0
        self.context_buffer = {}
        self.row_collection = False
        self._index = 0

        for data_loop in self.consume_queue(self.input_queue):
            if data_loop.elements is not None:
                self.ingest_loop(data_loop)
                continue

            # Closing loop (i.e. close loop)
            if data_loop.id == self.transaction_loop:
                yield self.emit_row(data_loop.meta or {})
                self.row_collection = False
                self.row_depth = data_loop.depth

            # # Note: This might be required upon closing loops
            # if data_loop.depth < self.row_depth:   # Now we get to parent loop of the transaction loop
            #     # Clear all the context beneath the parent loop
            #     # (i.e. siblings (and siblings children) of the transaction loop)
            #     for loop_id, depth in list(self.context_buffer.keys()):
            #         if depth > data_loop.depth:
            #             self.context_buffer.pop((loop_id, depth))

    def consume(self):
        headers, stream = self.field_hdr, self._consume()
        for tf in self.transforms:
            headers, stream = tf(headers, stream)

        return headers, stream

    def process(self):
        return self.writer.write(self)
