
# Update the release number
release RELEASE_TYPE:
    python3 '.command/pycmd/version-bump.py' -- {{RELEASE_TYPE}}
