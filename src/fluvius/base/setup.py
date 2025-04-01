import os
import re
import subprocess

from ast import literal_eval
from typing import Any, Callable


def run_command(command):
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False)
    results = p.communicate()
    if p.returncode != 0:
        raise ValueError("Command did not return success code [0].")

    return results


def get_version(source: str):
    try:
        git_tag, _ = run_command(["git", "rev-parse", "--short", "HEAD"])
        git_tag = git_tag.decode("utf-8").replace("\n", "")
        if not re.match(r"^[a-f0-9]{7}$", git_tag):
            raise ValueError("Not a valid git tag: {}".format(git_tag))
    except ValueError:
        git_tag = "nogit"

    with open(source) as f:
        for line in f:
            variable, _, expr = line.partition("=")
            variable, expr = variable.strip(), expr.lstrip()
            if variable == "__version__" and expr:
                return "{}+{}".format(literal_eval(expr), git_tag)

    raise ValueError("__version__ not found")


def get_requirements(source: str = "requirements.txt"):
    requirements = []
    with open(source) as f:
        for line in f:
            package, _, comment = line.partition("#")
            package = package.strip()
            if package:
                requirements.append(package)

    return requirements


def env(name: str, defval: Any, redacted: bool = False, coercer: Callable[[Any], Any] = None):
    ''' Extract environment value to use as configuration variable
    '''
    value = os.environ.get(name, defval)
    return coercer(value) if callable(coercer) else value
