"Various utility functions."

import datetime
import email.message
import hashlib
import logging
import os
import os.path
import smtplib
import string
import uuid
import unicodedata

import couchdb2
import yaml

from publications import constants
from publications import settings


def load_settings(filepath=None, log=True):
    """Load the settings. The file path first specified is used:
    1) The argument to this procedure (possibly from a command line argument).
    2) The environment variable PUBLICATIONS_SETTINGS.
    3) The file '../site/settings.yaml' relative to this directory.
    If 'log' is True, activate logging according to DEBUG settings.
    Raise IOError if settings file could not be read.
    Raise KeyError if a settings variable is missing.
    Raise ValueError if a settings variable value is invalid.
    """
    site_dir = settings["SITE_DIR"]
    if not os.path.exists(site_dir):
        raise IOError(f"The required site directory '{site_dir}' does not exist.")
    if not os.path.isdir(site_dir):
        raise IOError(f"The site directory path '{site_dir}' is not a directory.")
    # Find and read the settings file, updating the defaults.
    if not filepath:
        try:
            filename = os.environ["PUBLICATIONS_SETTINGS"]
        except KeyError:
            filepath = os.path.join(site_dir, "settings.yaml")
    with open(filepath) as infile:
        settings.update(yaml.safe_load(infile))
    settings["SETTINGS_FILE"] = filepath

    # Setup logging.
    if settings.get("LOGGING_DEBUG"):
        kwargs = dict(level=logging.DEBUG)
    else:
        kwargs = dict(level=logging.INFO)
    try:
        kwargs["format"] = settings["LOGGING_FORMAT"]
    except KeyError:
        pass
    try:
        kwargs["filename"] = settings["LOGGING_FILEPATH"]
    except KeyError:
        pass
    else:
        try:
            kwargs["filemode"] = settings["LOGGING_FILEMODE"]
        except KeyError:
            pass
    settings["LOG"] = log
    if log:
        logging.basicConfig(**kwargs)
        logging.info(f"Publications version {constants.VERSION}")
        logging.info(f"ROOT: {constants.ROOT}")
        logging.info(f"SITE_DIR: {settings['SITE_DIR']}")
        logging.info(f"settings: {settings['SETTINGS_FILE']}")
        logging.info(f"logging debug: {settings['LOGGING_DEBUG']}")
        logging.info(f"tornado debug: {settings['TORNADO_DEBUG']}")

    # Check some settings.
    for key in ["BASE_URL", "PORT", "DATABASE_SERVER", "DATABASE_NAME"]:
        if key not in settings:
            raise KeyError(f"No settings['{key}'] item.")
        if not settings[key]:
            raise ValueError(f"Settings['{key}'] has invalid value.")
    if len(settings.get("COOKIE_SECRET") or "") < 10:
        raise ValueError("settings['COOKIE_SECRET'] not set, or too short.")
    if len(settings.get("PASSWORD_SALT") or "") < 10:
        raise ValueError("Settings['PASSWORD_SALT'] not set, or too short.")
    for key in ["PUBMED_DELAY", "PUBMED_TIMEOUT", "CROSSREF_DELAY", "CROSSREF_TIMEOUT"]:
        if not isinstance(settings[key], (int, float)) or settings[key] <= 0.0:
            raise ValueError(f"Invalid '{key}' value: must be positive number.")

    # Set up the xref templates URLs.
    settings["XREF_TEMPLATE_URLS"] = NocaseDict(settings["XREF_TEMPLATE_URLS"])
    settings["XREF_TEMPLATE_URLS"]["URL"] = "%s"


def get_dbserver():
    "Return the CouchDB2 handle for the CouchDB server."
    kwargs = dict(href=settings["DATABASE_SERVER"])
    if settings.get("DATABASE_ACCOUNT") and settings.get("DATABASE_PASSWORD"):
        kwargs["username"] = settings["DATABASE_ACCOUNT"]
        kwargs["password"] = settings["DATABASE_PASSWORD"]
    return couchdb2.Server(**kwargs)


def get_db():
    """Return the CouchDB2 handle for the CouchDB database.
    The named database must exist.
    """
    server = get_dbserver()
    name = settings["DATABASE_NAME"]
    try:
        return server[name]
    except couchdb2.NotFoundError:
        raise KeyError(f"CouchDB database '{name}' does not exist.")


def load_design_documents():
    "Load the CouchDB design documents. Return the database."
    import publications.account
    import publications.blacklist
    import publications.journal
    import publications.label
    import publications.log
    import publications.publication
    import publications.researcher

    db = get_db()
    publications.account.load_design_document(db)
    publications.blacklist.load_design_document(db)
    publications.journal.load_design_document(db)
    publications.label.load_design_document(db)
    publications.log.load_design_document(db)
    publications.publication.load_design_document(db)
    publications.researcher.load_design_document(db)
    return db


def get_doc(db, designname, viewname, key):
    """Get the document with the given key from the given design view.
    Raise KeyError if not found.
    """
    view = db.view(designname, viewname, key=key, include_docs=True, reduce=False)
    result = list(view)
    if len(result) != 1:
        raise KeyError(f"{len(result)} items found")
    return result[0].doc


def get_docs(db, designname, viewname, key=None, last=None, **kwargs):
    """Get the list of documents using the given design view and
    the given key or interval.
    """
    if key is None:
        pass
    elif last is None:
        kwargs["key"] = key
    else:
        kwargs["startkey"] = key
        kwargs["endkey"] = last
    view = db.view(designname, viewname, include_docs=True, reduce=False, **kwargs)
    return [i.doc for i in view]


def get_count(db, designname, viewname, key=None):
    "Get the reduce value for the name view and the given key."
    if key is None:
        view = db.view(designname, viewname, reduce=True)
    else:
        view = db.view(designname, viewname, key=key, reduce=True)
    try:
        return list(view)[0].value
    except IndexError:
        return 0


def get_account(db, email):
    """Get the account identified by the email address.
    Raise KeyError if not found.
    """
    try:
        doc = get_doc(db, "account", "email", email.strip().lower())
    except KeyError:
        raise KeyError(f"no such account '{email}'")
    return doc


def get_publication(db, identifier):
    """Get the publication given its IUID, DOI or PMID.
    Raise KeyError if not found.
    """
    if not identifier:
        raise KeyError
    identifier = identifier.lower()
    try:
        doc = db[identifier]
    except couchdb2.NotFoundError:
        doc = None
        for viewname in ["doi", "pmid"]:
            try:
                doc = get_doc(db, "publication", viewname, identifier)
                break
            except KeyError:
                pass
        else:
            raise KeyError(f"no such publication '{identifier}'.")
    return doc


def get_researcher(db, identifier):
    """Get the researcher entity given its IUID or ORCID.
    Raise KeyError if not found.
    """
    if not identifier:
        raise KeyError
    try:
        doc = db[identifier.lower()]
    except couchdb2.NotFoundError:
        try:
            doc = get_doc(db, "researcher", "orcid", identifier)
        except KeyError:
            raise KeyError(f"no such researcher '{identifier}'.")
    return doc


def get_label(db, identifier):
    """Get the label document by its IUID or value.
    Raise KeyError if not found.
    """
    if not identifier:
        raise KeyError("no identifier provided")
    try:
        doc = db[identifier]
    except couchdb2.NotFoundError:
        identifier = to_ascii(identifier).lower()
        try:
            doc = get_doc(db, "label", "normalized_value", identifier)
        except KeyError:
            raise KeyError(f"no such label '{identifier}'")
    return doc


def get_blacklisted(db, identifier):
    """Get the blacklist document if the publication with
    the external identifier has been blacklisted.
    """
    if not identifier:
        return None
    for viewname in ["doi", "pmid"]:
        try:
            return get_doc(db, "blacklist", viewname, identifier)
        except KeyError:
            pass
    return None


def get_iuid():
    "Return a unique instance identifier."
    return uuid.uuid4().hex


def hashed_password(password):
    "Return the password in hashed form."
    sha256 = hashlib.sha256(settings["PASSWORD_SALT"].encode("utf-8"))
    sha256.update(password.encode("utf-8"))
    return sha256.hexdigest()


def check_password(password):
    """Check that the password is long and complex enough.
    Raise ValueError otherwise."""
    if len(password) < settings["MIN_PASSWORD_LENGTH"]:
        raise ValueError(
            "Password must be at least {0} characters.".format(
                settings["MIN_PASSWORD_LENGTH"]
            )
        )


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
    return dt.isoformat() + "Z"


def today(days=None):
    """Current date (UTC) in ISO format.
    Add the specified offset in days, if given.
    """
    instant = datetime.datetime.utcnow()
    if days:
        instant += datetime.timedelta(days=days)
    result = instant.isoformat()
    return result[: result.index("T")]


def to_date(value):
    """Convert value to proper ISO format date.
    Return today if None.
    Raise ValueError if cannot be interpreted.
    """
    if not value:
        return today()
    result = []
    parts = value.split("-")
    try:
        year = int(parts[0])
        try:
            month = int(parts[1])
            if month < 0:
                raise ValueError
            if month > 12:
                raise ValueError
        except IndexError:
            month = 0
        try:
            day = int(parts[2])
            if day < 0:
                raise ValueError
            if day > 31:
                raise ValueError
        except IndexError:
            day = 0
    except (TypeError, ValueError):
        raise ValueError(f"invalid date '{value}'")
    return "%s-%02i-%02i" % (year, month, day)


def years():
    "Return a list of years from the first year to the current."
    return list(range(settings["FIRST_YEAR"], int(today().split("-")[0]) + 1))


def to_ascii(value, alphanum=False):
    """Convert any non-ASCII character to its closest ASCII equivalent.
    'alphanum': retain only alphanumerical characters and whitespace.
    """
    if value is None:
        return ""
    value = unicodedata.normalize("NFKD", str(value))
    value = "".join([c for c in value if not unicodedata.combining(c)])
    if alphanum:
        alphanum = set(string.ascii_letters + string.digits + string.whitespace)
        value = "".join([c for c in value if c in alphanum])
    return value


def squish(value):
    "Remove all unnecessary white spaces."
    return " ".join([p for p in value.split() if p])


def to_bool(value):
    "Convert the value into a boolean, interpreting various string values."
    if isinstance(value, bool):
        return value
    if not value:
        return False
    lowvalue = value.lower()
    if lowvalue in constants.TRUE:
        return True
    if lowvalue in constants.FALSE:
        return False
    raise ValueError("invalid boolean: '{value}'")


def strip_prefix(value):
    "Strip any prefix from the string value."
    value = value.strip()
    lowcase = value.lower()
    for prefix in settings["IDENTIFIER_PREFIXES"]:
        if lowcase.startswith(prefix):
            return value[len(prefix) :].strip()
    return value


def get_formatted_authors(authors, complete=False):
    "Get formatted list of authors; partial or complete list."
    if (
        not complete
        and len(authors)
        > settings["NUMBER_FIRST_AUTHORS"] + settings["NUMBER_LAST_AUTHORS"]
    ):
        authors = (
            authors[: settings["NUMBER_FIRST_AUTHORS"]]
            + [None]
            + authors[-settings["NUMBER_LAST_AUTHORS"] :]
        )
    result = []
    for author in authors:
        if author:
            name = "%s %s" % (
                " ".join((author["family"] or "").split()),
                author.get("initials") or "",
            )
            # Get rid of bizarre newlines in author names.
            result.append(" ".join(name.strip().split()))
        else:
            result.append("...")
    return ", ".join(result)


class DownloadParametersMixin:
    """Mixin for getting the parameters controlling the download output.
    To be inherited by a RequestHandler subclass.
    """

    def get_parameters(self):
        "Return the output parameters from the form arguments."
        result = dict(
            single_label=to_bool(self.get_argument("single_label", False)),
            all_authors=to_bool(self.get_argument("all_authors", False)),
            issn=to_bool(self.get_argument("issn", False)),
            numbered=to_bool(self.get_argument("numbered", False)),
            doi_url=to_bool(self.get_argument("doi_url", False)),
            pmid_url=to_bool(self.get_argument("pmid_url", False)),
        )
        try:
            result["maxline"] = self.get_argument("maxline", None)
            if result["maxline"]:
                result["maxline"] = int(result["maxline"])
                if result["maxline"] <= 20:
                    raise ValueError
        except (ValueError, TypeError):
            result["maxline"] = None
        delimiter = self.get_argument("delimiter", "").lower()
        if delimiter == "comma":
            result["delimiter"] = ","
        elif delimiter == "semi-colon":
            result["delimiter"] = ";"
        elif delimiter == "tab":
            result["delimiter"] = "\t"
        encoding = self.get_argument("encoding", "").lower()
        if encoding:
            result["encoding"] = encoding
        return result


class EmailServer:
    "A connection to an email server for sending emails."

    def __init__(self):
        """Open the connection to the email server.
        Raise ValueError if no email server host has been defined
        or any other problem.
        """
        try:
            host = settings["EMAIL"]["HOST"]
            if not host:
                raise KeyError
            self.email = settings["SITE_EMAIL"]
            if not self.email:
                raise KeyError
        except (KeyError, TypeError):
            raise ValueError("email server host is not properly defined")
        try:
            port = settings["EMAIL"].get("PORT") or 0
            if settings["EMAIL"].get("SSL"):
                self.server = smtplib.SMTP_SSL(host, port=port)
            else:
                self.server = smtplib.SMTP(host, port=port)
                if settings["EMAIL"].get("TLS"):
                    self.server.starttls()
            self.server.ehlo()
            try:
                user = settings["EMAIL"]["USER"]
                password = settings["EMAIL"]["PASSWORD"]
            except KeyError:
                pass
            else:
                self.server.login(user, password)
        except smtplib.SMTPException as error:
            raise ValueError(str(error))

    def __del__(self):
        "Close the connection to the email server."
        try:
            self.server.quit()
        except (smtplib.SMTPException, AttributeError):
            pass

    def send(self, recipient, subject, text):
        "Send an email."
        try:
            message = email.message.EmailMessage()
            message["From"] = self.email
            message["Subject"] = subject
            message["Reply-To"] = settings["SITE_REPLY_TO_EMAIL"] or self.email
            message["To"] = recipient
            message.set_content(text)
            self.server.send_message(message)
        except smtplib.SMTPException as error:
            raise ValueError(str(error))


class NocaseDict:
    "Keys are compared ignoring case."

    def __init__(self, orig):
        self.orig = orig.copy()
        self.lower = dict()
        for key in orig:
            self.lower[key.lower()] = orig[key]

    def keys(self):
        return list(self.orig.keys())

    def __getitem__(self, key):
        return self.lower[key.lower()]

    def __setitem__(self, key, value):
        self.orig[key] = value
        self.lower[key.lower()] = value

    def __str__(self):
        return str(dict([(k, self[k]) for k in self.keys()]))

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default
