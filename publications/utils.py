"Various utility functions."

from __future__ import print_function

import datetime
import hashlib
import logging
import optparse
import os
import socket
import urlparse
import uuid
import unicodedata

import couchdb
import yaml

import publications
from . import constants
from . import settings


def get_command_line_parser(description=None):
    "Get the base command line argument parser."
    # optparse is used (rather than argparse) since
    # this code must be possible to run under Python 2.6
    parser = optparse.OptionParser(usage='usage: %prog [options]',
                                   description=description)
    parser.add_option('-s', '--settings',
                      action='store', dest='settings', default=None,
                      metavar="FILE", help="filename of settings YAML file")
    return parser

def load_settings(filepath=None):
    """Load and return the settings from the file path given by
    1) the argument to this procedure,
    2) the environment variable PUBLICATIONS_SETTINGS,
    3) the file '{hostname}.yaml' in this directory,
    4) the file 'settings.yaml' in this directory
    Raise ValueError if no settings file was given.
    Raise IOError if settings file could not be read.
    Raise KeyError if a settings variable is missing.
    Raise ValueError if a settings variable value is invalid.
    """
    if not filepath:
        filepath = os.environ.get('PUBLICATIONS_SETTINGS')
    if not filepath:
        hostname = socket.gethostname().split('.')[0]
        basedir = os.path.dirname(__file__)
        for filepath in [os.path.join(basedir, "{0}.yaml".format(hostname)),
                         os.path.join(basedir, 'settings.yaml')]:
            if os.path.exists(filepath) and os.path.isfile(filepath):
                break
        else:
            raise ValueError('No settings file specified.')
    # Read the settings file, updating the defaults
    with open(filepath) as infile:
        settings.update(yaml.safe_load(infile))
    settings['SETTINGS_FILEPATH'] = filepath
    # Expand environment variables (ROOT, SITE_DIR) once and for all
    for key, value in settings.items():
        if isinstance(value, str):
            settings[key] = expand_filepath(value)
    # Set logging state
    if settings.get('LOGGING_DEBUG'):
        kwargs = dict(level=logging.DEBUG)
    else:
        kwargs = dict(level=logging.INFO)
    try:
        kwargs['format'] = settings['LOGGING_FORMAT']
    except KeyError:
        pass
    try:
        kwargs['filename'] = settings['LOGGING_FILEPATH']
    except KeyError:
        pass
    try:
        kwargs['filemode'] = settings['LOGGING_FILEMODE']
    except KeyError:
        pass
    logging.basicConfig(**kwargs)
    logging.info("Publications version %s", publications.__version__)
    logging.info("settings from %s", settings['SETTINGS_FILEPATH'])
    if settings['LOGGING_DEBUG']:
        logging.info('logging debug')
    if settings['TORNADO_DEBUG']:
        logging.info('tornado debug')
    # Check settings
    for key in ['BASE_URL', 'DATABASE_SERVER', 'DATABASE_NAME']:
        if key not in settings:
            raise KeyError("No settings['{0}'] item.".format(key))
        if not settings[key]:
            raise ValueError("settings['{0}'] has invalid value.".format(key))
    if len(settings.get('COOKIE_SECRET') or '') < 10:
        raise ValueError("settings['COOKIE_SECRET'] not set, or too short.")
    if len(settings.get('PASSWORD_SALT') or '') < 10:
        raise ValueError("settings['PASSWORD_SALT'] not set, or too short.")
    # Settings computable from others
    settings['DATABASE_SERVER_VERSION'] = get_dbserver().version()
    if 'PORT' not in settings:
        parts = urlparse.urlparse(settings['BASE_URL'])
        items = parts.netloc.split(':')
        if len(items) == 2:
            settings['PORT'] = int(items[1])
        elif parts.scheme == 'http':
            settings['PORT'] =  80
        elif parts.scheme == 'https':
            settings['PORT'] =  443
        else:
            raise ValueError('Could not determine port from BASE_URL.')

def expand_filepath(filepath):
    "Expand environment variables (ROOT and SITE_DIR) in filepaths."
    filepath = os.path.expandvars(filepath)
    old = None
    while filepath != old:
        old = filepath
        try:
            filepath = filepath.replace('{SITE_DIR}', settings['SITE_DIR'])
        except KeyError:
            pass
        filepath = filepath.replace('{ROOT}', settings['ROOT'])
    return filepath

def get_dbserver():
    return couchdb.Server(settings['DATABASE_SERVER'])

def get_db(create=False):
    """Return the handle for the CouchDB database.
    If 'create' is True, then create the database if it does not exist.
    """
    server = get_dbserver()
    name = settings['DATABASE_NAME']
    try:
        return server[name]
    except couchdb.http.ResourceNotFound:
        if create:
            return server.create(name)
        else:
            raise KeyError("CouchDB database '%s' does not exist." % name)

def get_iuid():
    "Return a unique instance identifier."
    return uuid.uuid4().hex

def hashed_password(password):
    "Return the password in hashed form."
    sha256 = hashlib.sha256(settings['PASSWORD_SALT'])
    sha256.update(password)
    return sha256.hexdigest()

def check_password(password):
    """Check that the password is long and complex enough.
    Raise ValueError otherwise."""
    if len(password) < settings['MIN_PASSWORD_LENGTH']:
        raise ValueError("Password must be at least {0} characters long.".
                         format(settings['MIN_PASSWORD_LENGTH']))

def timestamp(days=None):
    """Current date and time (UTC) in ISO format, with millisecond precision.
    Add the specified offset in days, if given.
    """
    instant = datetime.datetime.utcnow()
    if days:
        instant += datetime.timedelta(days=days)
    instant = instant.isoformat()
    return instant[:17] + "%06.3f" % float(instant[17:]) + "Z"

def epoch_to_iso(epoch):
    """Convert the given number of seconds since the epoch
    to date and time in ISO format.
    """
    dt = datetime.datetime.fromtimestamp(float(epoch))
    return dt.isoformat() + 'Z'

def today(days=None):
    """Current date (UTC) in ISO format.
    Add the specified offset in days, if given.
    """
    instant = datetime.datetime.utcnow()
    if days:
        instant += datetime.timedelta(days=days)
    result = instant.isoformat()
    return result[:result.index('T')]

def to_ascii(value):
    "Convert any non-ASCII character to its closest ASCII equivalent."
    if not isinstance(value, unicode):
        value = unicode(value, 'utf-8')
    return unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')

def to_utf8(value):
    "Convert value to UTF-8 representation."
    if isinstance(value, basestring):
        if not isinstance(value, unicode):
            value = unicode(value, 'utf-8')
        return value.encode('utf-8')
    else:
        return value

def to_bool(value):
    "Convert the value into a boolean, interpreting various string values."
    if isinstance(value, bool): return value
    if not value: return False
    lowvalue = value.lower()
    if lowvalue in constants.TRUE: return True
    if lowvalue in constants.FALSE: return False
    raise ValueError(u"invalid boolean: '{}'".format(value))

def write_log(db, rqh, doc, changed=dict()):
    "Add a log entry for the change of the given entity."
    assert doc[constants.DOCTYPE] in constants.ENTITIES
    entry = dict(_id=get_iuid(),
                 doc=doc['_id'],
                 doctype=doc[constants.DOCTYPE],
                 changed=changed,
                 modified=timestamp())
    entry[constants.DOCTYPE] = constants.LOG
    if rqh:
        # xheaders argument to HTTPServer takes care of X-Real-Ip
        # and X-Forwarded-For
        entry['remote_ip'] = rqh.request.remote_ip
        try:
            entry['user_agent'] = rqh.request.headers['User-Agent']
        except KeyError:
            pass
    try:
        entry['account'] = rqh.current_user['email']
    except (AttributeError, TypeError, KeyError):
        pass
    db.save(entry)
