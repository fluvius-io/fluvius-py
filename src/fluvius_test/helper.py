import os

def _data(filename, *paths):
    return os.path.join('./tests/_data', *paths, filename)


def _conf(name):
    return _data(f'{name}.conf', 'cfg')


def _csv(name):
    return _data(f'{name}.csv', 'csv')


def _yml(name):
    return _data(f'{name}.yml', 'yml')
