from types import SimpleNamespace

class ImmutableNamespace(SimpleNamespace):
    def __setattr__(self, name, value):
        if hasattr(self, name):
            raise AttributeError(f"Cannot modify attribute '{name}'")
        super().__setattr__(name, value)

    def __delattr__(self, name):
        raise AttributeError(f"Cannot delete attribute '{name}'")



