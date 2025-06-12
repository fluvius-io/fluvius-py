import json
from fluvius.dmap.interface import DataLoop, DataElement
from fluvius.dmap.reader import BaseReader, register_reader


@register_reader('json')
class JsonReader(BaseReader):
    def generate_list(self, data):
        for idx, item in enumerate(data):
            if isinstance(item, (dict)):
                yield from self.traverse_data(data=item)
                continue

            yield DataElement(idx, item, None)

    def generate_dict(self, data):
        for key, value in data.items():
            if isinstance(value, (dict)):
                yield from self.traverse_data(data=value)
                continue

            yield DataElement(key, value, None)

    def traverse_data(self, data):
        if isinstance(data, dict):
            yield from self.generate_dict(data)
        elif isinstance(data, list):
            yield from self.generate_list(data)
        else:
            raise ValueError(
                f"Can not generate data of type {type(data)}: {data}"
            )

    def iter_data_loop(self, input_files):
        if not isinstance(input_files, list):
            _input_files = [input_files]

        for file_resource in _input_files:
            with open(file_resource.filepath, newline='') as jsonfile:
                json_data = json.load(jsonfile)

            for index, datum in enumerate(json_data, start=1):
                elements = tuple(self.traverse_data(data=datum))
                yield DataLoop(None, elements, 1, None)
                yield DataLoop(None, None, 1, None)
