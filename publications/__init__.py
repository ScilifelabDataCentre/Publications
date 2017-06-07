"Publications: Simple publications reference database with web interface."

from __future__ import print_function

import os

__version__ = '1.5.3'

# Default settings, may be changed by a settings YAML file.
settings = dict(
    ROOT=os.path.dirname(__file__),
    BASE_URL='http://localhost:8885/',
    PORT=8885,
    TORNADO_DEBUG=False,
    LOGGING_DEBUG=False,
    LOGGING_FORMAT='%(levelname)s [%(asctime)s] %(message)s',
    DATABASE_SERVER='http://localhost:5984/',
    DATABASE_NAME='publications',
    COOKIE_SECRET=None,         # Must be set!
    PASSWORD_SALT=None,         # Must be set!
    EMAIL=dict(HOST=None,       # No emails can be sent unless this is set.
               PORT=None,
               TLS=False,
               USER=None,
               PASSWORD=None,
               SENDER=None),
    MIN_PASSWORD_LENGTH=6,
    LOGIN_MAX_AGE_DAYS=14,
    SITE_NAME='Publications',
    SITE_HOME_TITLE='Publications',
    SITE_HOME_TEXT='A simple publications reference database system.',
    SITE_EMAIL=None,
    SITE_CONTACT='<p><i>No contact information available.</i></p>',
    SITE_DIR='static',
    SOURCE_HOME='https://github.com/pekrau/Publications',
    SOURCE_VERSION=__version__,
    SHORT_PUBLICATIONS_LIST_LIMIT=10,
    SHORT_AUTHORS_LIST_LIMIT=5,
    JQUERY_CSS='https://code.jquery.com/ui/1.12.1/themes/smoothness/jquery-ui.css',
    JQUERY_JS='https://code.jquery.com/jquery-1.12.4.min.js',
    JQUERY_UI_JS='https://code.jquery.com/ui/1.12.1/jquery-ui.min.js',
    BOOTSTRAP_CSS='https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css',
    BOOTSTRAP_THEME_CSS='https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap-theme.min.css',
    BOOTSTRAP_JS='https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js',
    DATATABLES_CSS='https://cdn.datatables.net/1.10.13/css/dataTables.bootstrap.min.css',
    DATATABLES_JQUERY_JS='https://cdn.datatables.net/1.10.13/js/jquery.dataTables.min.js',
    DATATABLES_BOOTSTRAP_JS='https://cdn.datatables.net/1.10.13/js/dataTables.bootstrap.min.js',
    )
