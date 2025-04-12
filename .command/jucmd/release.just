
# Update the release number
release RELEASE_TYPE RELEASE_LABEL="none":
    python3 '.command/pycmd/version-bump.py' -- {{RELEASE_TYPE}} {{RELEASE_LABEL}}
