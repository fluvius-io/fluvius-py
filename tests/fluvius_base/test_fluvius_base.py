from types import SimpleNamespace
from fluvius import setupModule


def test_setupModule():
    defaults = SimpleNamespace(TEST_CONFIG_KEY = 'sample-value')
    config, logger = setupModule('test_setupModule', defaults)
    assert config.TEST_CONFIG_KEY == 'sample-value'
