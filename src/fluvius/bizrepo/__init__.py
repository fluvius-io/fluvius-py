class BusinessArtifactRepository(object):
    ''' Central location to manage all business artifacts '''

    def __init__(self, name):
        self._name = name


class BusinessArtifact(object):
    def __init__(self, name, type, **kwargs):
        self._name = name
        self._type = type
        self._opts = kwargs
