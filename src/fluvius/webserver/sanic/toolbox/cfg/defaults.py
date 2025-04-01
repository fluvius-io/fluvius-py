import os
_BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

SETUP_MQTT_CLIENT = True
SETUP_UNAUTHORIZED_PAGE = True
STATIC_PATH = os.path.join(_BASE_PATH, 'static')
LANDING_PAGE_API_MANIFEST = os.path.join(_BASE_PATH, 'static/default_manifest.json')
TOOLBOX_PREFIX = "/~dev"
