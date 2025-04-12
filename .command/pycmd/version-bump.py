import sh
import click
import tomllib  # Python 3.11+
import re
from pathlib import Path
from collections import namedtuple

RX_PEP440_LABEL = re.compile(r"^(a|b|rc|post|dev)(\d*)$", re.VERBOSE)

PYPROJECT_PATH = Path("pyproject.toml")
INIT_PATH = Path("src/fluvius/__init__.py")  # 👈 Replace with your actual package path

Version = namedtuple("Version", ["major", "minor", "patch", "label"])

def parse_version_str(version_str):
    """Parse a version string like '1.2.3-final' into a Version namedtuple."""
    match = re.match(r"(\d+)\.(\d+)\.(\d+)-?([\w]*)", version_str)
    if not match:
        raise ValueError(f"Invalid version format: {version_str}")
    major, minor, patch, label = match.groups()
    return Version(int(major), int(minor), int(patch), label or "final")


def version_to_str(version):
    """Convert Version namedtuple to '1.2.3-final' string."""
    if version.label not in ('', 'final', 'none'):
        return f"{version.major}.{version.minor}.{version.patch}-{version.label}"

    return f"{version.major}.{version.minor}.{version.patch}"



def get_version():
    # Read from pyproject.toml
    with PYPROJECT_PATH.open("rb") as f:
        pyproject = tomllib.load(f)
    toml_version_str = pyproject["project"]["version"]

    # Read from __init__.py using regex
    init_content = INIT_PATH.read_text()
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', init_content)
    if not match:
        raise ValueError("No __version__ declaration found in __init__.py")
    init_version_str = match.group(1)

    # Compare both
    if toml_version_str != init_version_str:
        raise ValueError(
            f"Version mismatch:\n"
            f"  pyproject.toml: {toml_version_str}\n"
            f"  __init__.py:    {init_version_str}"
        )

    return parse_version_str(toml_version_str)


def set_version(version: Version):
    version_str = version_to_str(version)

    prompt = f'Commit all pending changes and set library version to: {version_str} \n>> Do you want to continue?'
    if not click.confirm(prompt, default=False):
        click.echo("❌ Action cancelled.")
        return

    # Update pyproject.toml
    pyproject_content = PYPROJECT_PATH.read_text()
    new_pyproject_content, count = re.subn(
        r'version\s*=\s*["\']([^"\']+)["\']',
        f'version = "{version_str}"',
        pyproject_content,
    )
    if count == 0:
        raise ValueError("Version field not found in pyproject.toml")

    PYPROJECT_PATH.write_text(new_pyproject_content)
    click.echo(f"[pyproject.toml] Updated to version {version_str}")

    # Update __init__.py
    init_content = INIT_PATH.read_text()
    new_init_content, count = re.subn(
        r'__version__\s*=\s*["\']([^"\']+)["\']',
        f'__version__ = "{version_str}"',
        init_content,
    )
    if count == 0:
        raise ValueError("No __version__ declaration found in __init__.py")

    INIT_PATH.write_text(new_init_content)
    click.echo(f"[{INIT_PATH}] __version__ updated to {version_str}")

    click.echo(sh.git('add', f'.'))
    click.echo(sh.git('commit', f'-m', f'Bump version to: {version_str}'))
    click.echo(sh.git('tag', f'releases/gh/{version_str}'))


@click.command()
@click.argument('release_type')
@click.argument('release_label', nargs=-1)
def update_release(release_type, release_label=None):
    current = get_version()
    if isinstance(release_label, tuple):
        release_label = release_label[0]

    if not release_label or release_label.strip().lower() == 'none':
        release_label =  None

    if release_label and not RX_PEP440_LABEL.match(release_label):
        raise ValueError(f'Invalid release label [{release_label}]. Must follow PEP-440.')


    match release_type.lower():
        case 'major':
            next_version = Version(current.major + 1, 0, 0, release_label or current.label)
            set_version(next_version)
        case 'minor':
            next_version = Version(current.major, current.minor + 1, 0, release_label or current.label)
            set_version(next_version)
        case 'patch':
            next_version = Version(current.major, current.minor, current.patch + 1, release_label or current.label)
            set_version(next_version)
        case 'label':
            if not release_label:
                raise ValueError('Release label is not provided.')

            next_version = Version(current.major, current.minor, current.patch, release_label)
            set_version(next_version)
        case _:
            click.echo("Current version:", version_to_str(current))
    return 0


if __name__ == '__main__':
    update_release()
