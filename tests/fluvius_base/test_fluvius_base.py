from types import SimpleNamespace


def test_setup_module():
    from fluvius import setupModule

    defaults = SimpleNamespace(TEST_CONFIG_KEY = 'sample-value')
    config, logger = setupModule('test_setupModule', defaults)
    assert config.TEST_CONFIG_KEY == 'sample-value'


def test_hashes():
    from fluvius.auth.hashes import check_hash, make_hash

    HASH_STRINGS = [
        "Hello, world!",                  # English (ASCII)
        "你好，世界",                      # Chinese
        "مرحبا بالعالم",                 # Arabic
        "😀🔥🚀",                          # Emojis
        "∑ ∫ √ π ∞",                     # Math symbols
        "Café résumé naïve",             # Accented characters
        "नमस्ते दुनिया",                 # Hindi (Devanagari)
        "Привет, мир",                   # Russian (Cyrillic)
        "שלום עולם",                    # Hebrew
        "\u03C0",                        # Greek letter pi (π)
        "\U0001F60E",                    # 😎 emoji via Unicode code point
        "\u2602 \u2603 \u2764",          # ☂ ☃ ❤ using escape sequences
        u"Unicode string in Python 3",   # Python 3 Unicode string

        # 🔐 Password-like Unicode strings
        "P@ssw🔥rd123",                   # Basic strong password with emoji
        "Cømpl3x🔐Şţřïñĝ!",              # Accented characters + emoji
        "密码🔑123!",                     # Chinese + numbers + emoji
        "Пароль💥Secure1!",              # Cyrillic + emoji
        "🔒🔑🧬AßcDé123!",              # Emojis + accented + ASCII
        "\u0040\u03C0\u2665\u2764",      # @π♥❤ in Unicode escapes
        "S3cur3🌍Wørld_#2025"             # Password with mixed scripts and symbols
    ]

    for s in HASH_STRINGS:
        h = make_hash(s)
        assert check_hash(s, h)
        assert not check_hash(s[:-1] + '.', h)
