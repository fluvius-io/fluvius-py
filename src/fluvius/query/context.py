from pyrsistent import PClass, field


class QueryContext(PClass):
    user = field()
