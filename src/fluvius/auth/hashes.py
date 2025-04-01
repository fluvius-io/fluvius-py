#!/usr/bin/env python3

import os
import hashlib
import random

from base64 import b64decode, b64encode

# Parameters to PBKDF2. Only affect new passwords.
SALT_LENGTH = 12
KEY_LENGTH = 66
HASH_FUNCTION = "sha256"  # Must be in hashlib.
# Linear to the hashing time. Adjust to be high but take a reasonable
# amount of time on your server. Measure with:
# python -m timeit -s 'import passwords as p' 'p.make_hash("something")'
COST_FACTOR = 9901


# hashlib.pbkdf2_hmac(hash_name, password, salt, iterations, dklen=None)
#
# The function provides PKCS#5 password-based key derivation function 2. It
# uses HMAC as pseudorandom function.
#
# The string hash_name is the desired name of the hash digest algorithm for
# HMAC, e.g. ‘sha1’ or ‘sha256’. password and salt are interpreted as buffers of
# bytes. Applications and libraries should limit password to a sensible length (
# e.g. 1024). salt should be about 16 or more bytes from a proper source,
# e.g. os.urandom().
#
# The number of iterations should be chosen based on the hash algorithm and
# computing power. As of 2013, at least 100,000 iterations of SHA-256 are
# suggested.
#
# dklen is the length of the derived key. If dklen is None then the digest size
# of the hash algorithm hash_name is used, e.g. 64 for SHA-512.


def make_hash(password):
    '''Generate a random salt and return a new hash for the password.'''
    if isinstance(password, str):
        passwd = bytearray(password, "utf-8")
    elif isinstance(password, (bytearray, bytes)):
        passwd = password
    else:
        raise ValueError(
            "Password must be either a string or bytes: {}".format(type(password)))

    salt = b64encode(os.urandom(SALT_LENGTH))
    hashbytes = hashlib.pbkdf2_hmac(
        HASH_FUNCTION, passwd, salt, COST_FACTOR, KEY_LENGTH)

    return "$".join(
        [
            "PBKDF2",
            HASH_FUNCTION,
            str(COST_FACTOR),
            str(salt, "ascii"),
            str(b64encode(hashbytes), "ascii"),
        ]
    )


def check_hash(password, hash_):
    if isinstance(password, str):
        passwd = bytearray(password, "ascii")
    elif isinstance(password, (bytearray, bytes)):
        passwd = password
    else:
        raise ValueError(
            "Password must be either a string or bytes: {}".format(type(password)))

    '''Check a password against an existing hash.'''
    algorithm, hash_function, cost_factor, salt, hash_a = hash_.split("$")
    # salt   = b64decode(salt)
    salt = bytearray(salt, "ascii")
    assert algorithm == "PBKDF2"
    hash_a = b64decode(hash_a)
    hash_b = hashlib.pbkdf2_hmac(hash_function, passwd, salt,
                                 int(cost_factor), len(hash_a))
    # Same as "return hash_a == hash_b" but takes a constant time.
    # See http://carlos.bueno.org/2011/10/timing.html
    diff = 0
    for char_a, char_b in zip(hash_a, hash_b):
        diff |= char_a ^ char_b

    return diff == 0


def secret_coverage(value):
    hash = make_hash(value)
    suffix = value[-2:]
    return f"{hash}:{suffix}"


def generate_base32_code(length=6):
    base32_code = [
        'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K',
        'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V',
        'W', 'X', 'Y', 'Z', '2', '3', '4', '5', '6', '7']
    random_code = random.choices(base32_code, k=length)
    return "".join(random_code)


if __name__ == '__main__':
    import sys
    if len(sys.argv) == 2:
        print(make_hash(sys.argv[1]))
    elif len(sys.argv) == 3:
        print(check_hash(sys.argv[1], sys.argv[2]))
    else:
        print(f'Generate password hash.')
        print(f' - Usage: {sys.argv[0]} <password>')
        print(f'')
        print(f'Check password hash')
        print(f' - Usage: {sys.argv[0]} <password> <hash_check>')
