import os
import hashlib
import mimetypes


def file_mime(filepath):
    content_type, encoding = mimetypes.guess_type(filepath)
    return content_type or 'application/x-binary'


def file_checksum_sha256(filename, block_size=65536):
    sha256 = hashlib.sha256()
    with open(filename, "rb") as f:
        for block in iter(lambda: f.read(block_size), b""):
            sha256.update(block)
    return sha256.hexdigest()


def file_basename(filepath):
    return os.path.basename(filepath)


def file_extension(filepath):
    basename = os.path.basename(filepath)
    _, extension = os.path.splitext(basename)
    if "." in extension:
        extension = extension[extension.index(".") + 1:]
    return extension


@contextmanager
def tempinput(fileobj):
    ''' GridOut files cannot be passed as filename to other functions
        therefore we need to wrap it within a temporary file and return the filename
        Note: file will be removed upon ending 'with' statetement.
        Usage:

            with tempinput(<gridout-filestream>) as filename:
                ...
    '''

    if isinstance(fileobj, str):
        yield fileobj
        return

    temp = tempfile.NamedTemporaryFile(delete=False)
    shutil.copyfileobj(fileobj, temp)
    temp.close()
    yield temp.name
    os.unlink(temp.name)


@contextmanager
def tempinputs(*files):
    contexts = [tempinput(f) for f in files]
    yield [ctx.__enter__() for ctx in contexts]
    for ctx in contexts:
        ctx.__exit__(None, None, None)


def safe_filename(filename: str, extension: Optional[str] = None):
    if extension:
        parts = filename.split(".")
        if len(parts) > 1:
            parts = parts[:-1]
        ext = extension.split(".")
        ''' Filter for empty strings. I.e. double dots [..] '''
        filename = ".".join(filter(lambda x: x, chain(parts, ext)))
    ''' Filename sanitization. Otherwise some files won't be extractable on Windows'''
    return "".join(e for e in filename if e not in "@/\\;,><&*:%=+!#^|?")


def ensure_path(*args):
    path = os.path.join(*args)
    if not os.path.exists(path):
        os.makedirs(path)

    return path
