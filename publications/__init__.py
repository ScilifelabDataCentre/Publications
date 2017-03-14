"Publications: Simple publications reference database with web interface."

import os

__version__ = '0.1.0'

# Default settings, may be changed by a settings YAML file.
settings = dict(
    ROOT=os.path.dirname(__file__),
    BASE_URL='http://localhost:8885/',
    TORNADO_DEBUG=False,
    LOGGING_DEBUG=False,
    LOGGING_FORMAT='%(levelname)s [%(asctime)s] %(message)s',
    DATABASE_SERVER='http://localhost:5984/',
    DATABASE_NAME='publications',
    COOKIE_SECRET=None,         # Must be set!
    PASSWORD_SALT=None,         # Must be set!
    MIN_PASSWORD_LENGTH=6,
    LOGIN_MAX_AGE_DAYS=14,
    SITE_NAME='Publications',
    SITE_DIR='{ROOT}/static',
    SOURCE_HOME='https://github.com/pekrau/Publications',
    )
