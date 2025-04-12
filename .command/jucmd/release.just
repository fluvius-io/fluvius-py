
# Update the release number (e.g. `just release patch post1`)
release RELEASE_TYPE RELEASE_LABEL="none":
    python3 '.command/pycmd/version-bump.py' -- {{RELEASE_TYPE}} {{RELEASE_LABEL}}
