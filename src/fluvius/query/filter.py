"""
    - Field Filters (operator on fields)
    - Composite Filters (operate on other filters)
"""
from pydantic import BaseModel, Field
from pprint import pprint

class InputSpec(dict):
    def __init__(self, type, **kwargs):
        super().__init__(type=type, **kwargs)


class FilterPreset(object):
    REGISTRY = {}
    def __init_subclass__(cls, name):
        if name in FilterPreset.REGISTRY:
            raise ValueError("Preset already register")

        filters = {}
        for attr in dir(cls):
            flt = getattr(cls, attr)
            if not (flt and isinstance(flt, Filter)):
                continue

            filters[attr] = flt

        cls.filters = filters
        FilterPreset.REGISTRY[name] = filters


    @classmethod
    def get(cls, name):
        return cls.REGISTRY[name]


class Filter(BaseModel):
    label: str
    dtype: str
    input: str | dict = "text"

    def __init__(self, label, dtype="string", **kwargs):
        super().__init__(label=label, dtype=dtype, **kwargs)


class FieldFilter(BaseModel):
    index: int = 10
    field: str
    label: str
    dtype: str
    input: dict


class CompositeFilter(BaseModel):
    """
    Composite filter input are always a list other filters
    """
    index: int = 1
    operator: str
    label: str



class UUIDFilterPreset(FilterPreset, name="uuid"):
    eq = Filter("Equal", "uuid")


class StringFilterPreset(FilterPreset, name="string"):
    eq = Filter("Equal", "string")
    ilike = Filter("Contains", "string")

class IntegerFilterPreset(FilterPreset, name="integer"):
    eq = Filter("Equal", dtype="integer", input="number")
    ilike = Filter("Contains", dtype="integer", input="number")

class CustomFilterPreset(IntegerFilterPreset, name="integer:custom"):
    eq = None
    gte = Filter("Greater or Equal", dtype="integer", input="number")


if __name__ == "__main__":

    class User(BaseModel):
        id: int = Field(description="User ID", preset="uuid", alias="_id")
        name: str = Field(alias="full_name", description="Full name of the user", preset="string")
        age: int | None = Field(default=None, ge=0, description="Optional age", preset="integer:custom")

    filters = {}
    counter = 10
    for name, field in User.__pydantic_fields__.items():
        meta = field.json_schema_extra
        filter_preset = meta["preset"]
        for k, v in FilterPreset.get(filter_preset).items():
            counter += 1
            filters[f"{field.alias or name}.{k}"] = FieldFilter(
                index = counter,
                field = name,
                label = v.label,
                dtype = v.dtype,
                input = InputSpec(**v.input) if isinstance(v.input, dict) else InputSpec(v.input),
            )

    pprint(filters)
