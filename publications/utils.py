"Various utility functions."

from __future__ import print_function

import argparse
import datetime
import email.mime.text
import hashlib
import logging
import optparse
import os
import socket
import smtplib
import urlparse
import uuid
import unicodedata

import couchdb
import yaml

import publications
from . import constants
from . import designs
from . import settings


REV_ERROR = 'Has been edited by someone else. Cannot overwrite.'

class NocaseDict(object):
    "Keys are compared ignoring case."
    def __init__(self, orig):
        self.orig = orig.copy()
        self.lower = dict()
        for key in orig:
            self.lower[key.lower()] = orig[key]
    def keys(self):
        return self.orig.keys()
    def __getitem__(self, key):
        return self.lower[key.lower()]


def get_command_line_parser(description=None):
    "Get the base command line argument parser."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-s', '--settings',
                        action='store', dest='settings', default=None,
                        metavar='FILE', help='filename of settings YAML file')
    return parser

def load_settings(filepath=None, ignore_logging_filepath=False):
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
            raise ValueError('Cannot find any settings file.')
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
    if not ignore_logging_filepath:
        try:
            kwargs['filename'] = settings['LOGGING_FILEPATH']
        except KeyError:
            pass
        else:
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
    # Use caseless dictionary for the xref templates URLs
    settings['XREF_TEMPLATE_URLS'] = NocaseDict(settings['XREF_TEMPLATE_URLS'])

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
    server = couchdb.Server(settings['DATABASE_SERVER'])
    if settings.get('DATABASE_ACCOUNT') and settings.get('DATABASE_PASSWORD'):
        server.resource.credentials = (settings.get('DATABASE_ACCOUNT'),
                                       settings.get('DATABASE_PASSWORD'))
    return server

def get_db():
    """Return the handle for the CouchDB database.
    The named database must exist.
    """
    server = get_dbserver()
    name = settings['DATABASE_NAME']
    try:
        return server[name]
    except couchdb.http.ResourceNotFound:
        raise KeyError("CouchDB database '%s' does not exist." % name)

def initialize(db=None):
    "Load the design documents, or update."
    if db is None:
        db = get_db()
    designs.load_design_documents(db)

def get_doc(db, key, viewname=None):
    """Get the document with the given i, or from the given view.
    Raise KeyError if not found.
    """
    if viewname is None:
        try:
            return db[key]
        except couchdb.ResourceNotFound:
            raise KeyError
    else:
        result = list(db.view(viewname, include_docs=True, reduce=False)[key])
        if len(result) != 1:
            raise KeyError("%i items found", len(result))
        return result[0].doc

def get_docs(db, viewname, key=None, last=None, **kwargs):
    """Get the list of documents using the named view and
    the given key or interval.
    """
    view = db.view(viewname, include_docs=True, reduce=False, **kwargs)
    if key is None:
        iterator = view
    elif last is None:
        iterator = view[key]
    else:
        iterator = view[key:last]
    return [i.doc for i in iterator]

def get_account(db, email):
    """Get the account identified by the email address.
    Raise KeyError if no such account.
    """
    try:
        doc = get_doc(db, email.strip().lower(), 'account/email')
    except KeyError:
        raise KeyError("no such account %s" % email)
    if doc[constants.DOCTYPE] != constants.ACCOUNT:
        raise KeyError("document %s is not an account" % email)
    return doc

def get_publication(db, identifier):
    """Get the publication given its IUID, DOI or PMID.
    Raise KeyError if no such publication.
    """
    if not identifier: raise KeyError
    identifier = identifier.lower()
    try:
        doc = get_doc(db, identifier)
    except KeyError:
        doc = None
        for viewname in ['publication/doi', 'publication/pmid']:
            try:
                doc = get_doc(db, identifier, viewname=viewname)
                break
            except KeyError:
                pass
        else:
            raise KeyError("no such publication %s" % identifier)
    if doc[constants.DOCTYPE] != constants.PUBLICATION:
        raise KeyError("document %s is not a publication" % identifier)
    return doc

def get_label(db, identifier):
    """Get the label document by its IUID or value.
    Raise KeyError if no such label.
    """
    if not identifier: raise KeyError('no identifier provided')
    try:
        doc = get_doc(db, identifier)
    except KeyError:
        identifier = to_ascii(identifier).lower()
        try:
            doc = get_doc(db, identifier, 'label/normalized_value')
        except KeyError:
            raise KeyError("no such label '%s'" % identifier)
    if doc[constants.DOCTYPE] != constants.LABEL:
        raise KeyError("wrong document type '%s'", doc[constants.DOCTYPE])
    return doc

def get_blacklisted(db, identifier):
    """Get the blacklist document if the publication with
    the external identifier has been blacklisted.
    """
    if not identifier: return None
    for viewname in ['blacklist/doi', 'blacklist/pmid']:
        try:
            return get_doc(db, identifier, viewname)
        except KeyError:
            pass
    return None

def get_iuid():
    "Return a unique instance identifier."
    return uuid.uuid4().hex

def hashed_password(password):
    "Return the password in hashed form."
    sha256 = hashlib.sha256(settings['PASSWORD_SALT'])
    sha256.update(to_utf8(password))
    return sha256.hexdigest()

def check_password(password):
    """Check that the password is long and complex enough.
    Raise ValueError otherwise."""
    if len(password) < settings['MIN_PASSWORD_LENGTH']:
        raise ValueError("Password must be at least {0} characters.".
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

def to_date(value):
    """Convert value to proper ISO format date.
    Return today if None.
    Raise ValueError if cannot be interpreted.
    """
    if not value:
        return today()
    result = []
    parts = value.split('-')
    try:
        year = int(parts[0])
        try:
            month = int(parts[1])
            if month < 0: raise ValueError
            if month > 12: raise ValueError
        except IndexError:
            month = 0
        try:
            day = int(parts[2])
            if day < 0: raise ValueError
            if day > 31: raise ValueError
        except IndexError:
            day = 0
    except (TypeError, ValueError):
        raise ValueError("invalid date '%s'" % value)
    return "%s-%02i-%02i" % (year, month, day)

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

def write_safe_csv_row(writer, row):
    """Remove any beginning character '=-+@' from string values to output.
    See http://georgemauer.net/2017/10/07/csv-injection.html
    """
    row = list(row)
    for pos, value in enumerate(row):
        if not isinstance(value, basestring): continue
        while len(value) and value[0] in '=-+@':
            value = value[1:]
        row[pos] = value
    writer.writerow(row)

PREFIXES = ['doi:', 'pmid:', 'pubmed:', 
            'http://doi.org/', 'https://doi.org/', 'http://dx.doi.org/']

def strip_prefix(value):
    "Strip any prefix from the string value."
    value = value.strip()
    lowcase = value.lower()
    for prefix in PREFIXES:
        if lowcase.startswith(prefix):
            return value[len(prefix)-1:].strip()
    return value

def get_formatted_authors(authors, complete=False):
    "Get formatted list of authors. 2+2 if not complete."
    if complete or len(authors) <= 4:
        result = ["%s %s" % (a['family'], a['initials'] or '')
                  for a in authors]
    else:
        result = ["%s %s" % (a['family'], a['initials'] or '')
                  for a in authors[:2]]
        result.append('...')
        result.extend(["%s %s" % (a['family'], a['initials'] or '')
                       for a in authors[-2:]])
    return ', '.join(result)


class EmailServer(object):
    "A connection to an email server for sending emails."

    def __init__(self):
        """Open the connection to the email server.
        Raise ValueError if no email server host has been defined.
        """
        host = settings['EMAIL']['HOST']
        if not host:
            raise ValueError('no email server host defined')
        try:
            port = settings['EMAIL']['PORT']
        except KeyError:
            self.server = smtplib.SMTP(host)
        else:
            self.server = smtplib.SMTP(host, port=port)
        if settings['EMAIL'].get('TLS'):
            self.server.starttls()
        try:
            user = settings['EMAIL']['USER']
            password = settings['EMAIL']['PASSWORD']
        except KeyError:
            pass
        else:
            self.server.login(user, password)
        self.email = settings.get('SITE_EMAIL') or settings['EMAIL']['SENDER']

    def __del__(self):
        "Close the connection to the email server."
        try:
            self.server.quit()
        except AttributeError:
            pass

    def send(self, recipient, subject, text):
        "Send an email."
        mail = email.mime.text.MIMEText(text, 'plain', 'utf-8')
        mail['Subject'] = subject
        mail['From'] = self.email
        mail['To'] = recipient
        self.server.sendmail(self.email, [recipient], mail.as_string())
