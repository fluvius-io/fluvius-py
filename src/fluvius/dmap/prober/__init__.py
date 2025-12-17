from slugify import slugify
from ruamel import yaml
from fluvius.error import BadRequestError
from fluvius.dmap import config
from fluvius.dmap.interface import ResourceMeta, ReaderFinished, ReaderError

quote = yaml.scalarstring.SingleQuotedScalarString

MAPPING_FIXTURES = {
    '_PRID': f"{config.BUILTIN_FIELD_PRID}|integer",
    '_COUNTER': f"{config.BUILTIN_FIELD_COUNTER}|integer",
    '_INDEX': f"{config.BUILTIN_FIELD_INDEX}|integer"
}

BUILTINS = {
    'Line No.': '_line',
    'Sequence No.': '_sequence',
    'Index No.': '_index'
}


def fname(ele_name):
    if ele_name in BUILTINS:
        return BUILTINS[ele_name]
    return slugify(ele_name, separator="_")


class DatamapProber(object):
    def __init__(self, fetcher, reader):
        self._fetcher = fetcher
        self._reader = reader
        self._tables = {}

    @property
    def tables(self):
        return self._tables

    def gen_mappings(self, datamap):
        mapping = {}

        def _gen():
            for k, v in MAPPING_FIXTURES.items():
                yield k, quote(v)

            for k, v in datamap.items():
                yield v, quote(k)

        for dst, src in _gen():
            if dst not in mapping:
                mapping[dst] = src
                continue

            if isinstance(mapping[dst], list):
                mapping[dst].append(src)
            else:
                mapping[dst] = [mapping[dst], src]

        return mapping

    def gen_config(self):
        for loop_id, table_meta in self.tables.items():
            spec = {
                'mapping': self.gen_mappings(table_meta['datamap'])
            }

            if loop_id is not None:
                spec['transaction'] = loop_id

            yield table_meta['key'], spec

    def probe(self):
        def check_variant():
            variant = 'STARTING'
            filepath = None

            r = self._reader
            if variant == 'STARTING':
                variant = r.variant
                filepath = r.filepath
            elif r.variant != variant:
                raise BadRequestError(
                    "T00.191",
                    f"Readers have different variant [{variant}] != [{r.variant}] ({filepath}, {r.filepath})",
                    None
                )

        def read():
            # check_variant()
            for file_resource in self._fetcher.fetch():
                yield from self._reader.read_file(file_resource)

        for data_loop in read():
            if isinstance(data_loop, ReaderError):
                raise ReaderError

            if isinstance(data_loop, ResourceMeta):
                continue

            if data_loop == ReaderFinished:
                continue

            if data_loop is None:
                break

            if data_loop.elements is None:
                continue

            if data_loop.id not in self.tables:
                try:
                    name = data_loop.meta.name
                except AttributeError:
                    name = data_loop.id if data_loop.id else 'default'

                self.tables[data_loop.id] = {
                    "key": slugify(name),
                    "datamap": {}
                }

            table_meta = self.tables[data_loop.id]
            datamap = table_meta['datamap']

            for ele in data_loop.elements:
                if ele.key in datamap:
                    continue

                try:
                    _, _, _, ele_name = ele.meta
                except TypeError:
                    ele_name = ele.key

                datamap[ele.key] = fname(ele_name)

    def write_config(self, filepath):
        cfg = dict(self.gen_config())
        if not (filepath.endswith('.yml') or filepath.endswith('.yaml')):
            filepath = f'{filepath}.yml'

        with open(filepath, 'w', encoding="utf-8") as yaml_file:
            yaml_in = yaml.YAML(typ='rt', pure=True)
            yaml_in.dump(cfg, yaml_file)
