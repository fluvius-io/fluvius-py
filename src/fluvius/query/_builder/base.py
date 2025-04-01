class QueryBuilder(object):
    def __init__(self, resource):
        self.lookup = {op.__key__: op for op in resource.gen_params()}
        self.fieldset = set(resource.__fieldmap__.keys())
        self.fielddef = set(
            k for k, v in resource.__fieldmap__.items() if not v.hidden
        )

    def meta(self):
        def _gen():
            seen = set()
            for c in self.lookup.values():
                if c in seen:
                    continue

                yield c.meta()
                seen.add(c)

        return list(_gen())
