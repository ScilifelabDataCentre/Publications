"Publications: A publications reference database with web interface."

import os.path
import re
import sys

__version__ = "9.2.1"


class Constants:
    def __setattr__(self, key, value):
        raise ValueError("cannot set constant")

    VERSION = __version__
    URL = "https://github.com/pekrau/Publications"

    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    TEMPLATE_DIR = os.path.normpath(os.path.join(ROOT_DIR, "templates"))
    STATIC_DIR = os.path.normpath(os.path.join(ROOT_DIR, "static"))
    SITE_DIR = os.path.normpath(os.path.join(ROOT_DIR, "../site"))

    PYTHON_VERSION = ".".join([str(i) for i in sys.version_info[0:3]])
    PYTHON_URL = "https://www.python.org/"
    TORNADO_URL = "http://tornadoweb.org/"
    CERTIFI_URL = "https://pypi.org/project/certifi/"
    COUCHDB_URL = "https://couchdb.apache.org/"
    COUCHDB2_URL = "https://pypi.org/project/couchdb2"
    XLSXWRITER_URL = "https://pypi.org/project/XlsxWriter/"
    PYYAML_URL = "https://pypi.org/project/PyYAML/"
    PYPARSING_URL = "https://pypi.org/project/pyparsing/"
    REQUESTS_URL = "https://docs.python-requests.org/"

    BOOTSTRAP_URL = "https://getbootstrap.com/"
    BOOTSTRAP_VERSION = "3.4.1"
    BOOTSTRAP_CSS_URL = (
        "https://stackpath.bootstrapcdn.com/bootstrap/3.4.1/css/bootstrap.min.css"
    )
    BOOTSTRAP_CSS_INTEGRITY = (
        "sha384-HSMxcRTRxnN+Bdg0JdbxYKrThecOKuH5zCYotlSAcp1+c8xmyTe9GYg1l9a69psu"
    )
    BOOTSTRAP_THEME_CSS_URL = (
        "https://stackpath.bootstrapcdn.com/bootstrap/3.4.1/css/bootstrap-theme.min.css"
    )
    BOOTSTRAP_THEME_CSS_INTEGRITY = (
        "sha384-6pzBo3FDv/PJ8r2KRkGHifhEocL+1X2rVCTTkUfGk7/0pbek5mMa1upzvWbrUbOZ"
    )
    BOOTSTRAP_JS_URL = (
        "https://stackpath.bootstrapcdn.com/bootstrap/3.4.1/js/bootstrap.min.js"
    )
    BOOTSTRAP_JS_INTEGRITY = (
        "sha384-aJ21OjlMXNL5UyIl/XNwTMqvzeRMZH2w8c5cRVpzpU8Y5bApTppSuUkhZXN0VxHd"
    )

    JQUERY_URL = "https://jquery.com/"
    JQUERY_VERSION = "1.12.4"
    JQUERY_UI_CSS_URL = "https://code.jquery.com/ui/1.12.1/themes/base/jquery-ui.css"
    JQUERY_JS_URL = "https://code.jquery.com/jquery-1.12.4.min.js"
    JQUERY_JS_INTEGRITY = "sha256-ZosEbRLbNQzLpnKIkEdrPv7lOy9C27hHQ+Xp8a4MxAQ="
    JQUERY_UI_JS_URL = "https://code.jquery.com/ui/1.12.1/jquery-ui.min.js"
    JQUERY_UI_JS_INTEGRITY = "sha256-VazP97ZCwtekAsvgPBSUwPFKdrwD3unUfSGVYrahUqU="

    JQUERY_LOCALTIME_URL = "https://plugins.jquery.com/jquery.localtime/"
    JQUERY_LOCALTIME_VERSION = "0.9.1"
    JQUERY_LOCALTIME_FILENAME = "jquery.localtime-0.9.1.min.js"

    DATATABLES_URL = "https://datatables.net/"
    DATATABLES_VERSION = "1.11.3"
    DATATABLES_CSS_URL = (
        "https://cdn.datatables.net/v/bs/jqc-1.12.4/dt-1.11.3/datatables.min.css"
    )
    DATATABLES_JS_URL = "https://cdn.datatables.net/1.11.3/js/jquery.dataTables.min.js"
    DATATABLES_BOOTSTRAP_JS_URL = (
        "https://cdn.datatables.net/1.11.3/js/dataTables.bootstrap.min.js"
    )

    LOGGING_FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"

    # Patterns
    ID_RX = re.compile(r"^[a-z][_a-z0-9]*$", re.IGNORECASE)
    NAME_RX = re.compile(r"^[^/]+$")
    IUID_RX = re.compile(r"^[0-9a-f]{32}$")
    DATE_RX = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")  # Safe until 9999 CE...
    EMAIL_RX = re.compile(r"^[^@]+@[^@]+\.[^@]+$")
    PMID_RX = re.compile(r"^[1-9]\d*$")

    # CouchDB
    # For view ranges: CouchDB uses the Unicode Collation Algorithm,
    # which is not the same as the ASCII collation sequence.
    # The endkey is inclusive, by default.
    CEILING = "ZZZZZZZZ"

    # Entity documents
    DOCTYPE = "publications_doctype"
    PUBLICATION = "publication"
    JOURNAL = "journal"
    ACCOUNT = "account"
    RESEARCHER = "researcher"
    LABEL = "label"
    BLACKLIST = "blacklist"
    LOG = "log"
    META = "meta"
    ENTITIES = (PUBLICATION, JOURNAL, ACCOUNT, LABEL, RESEARCHER)

    # Account roles
    ADMIN = "admin"
    CURATOR = "curator"
    ROLES = (ADMIN, CURATOR)

    LOGIN_URL = r"/login"

    # Boolean string values
    TRUE = frozenset(["true", "yes", "t", "y", "1"])
    FALSE = frozenset(["false", "no", "f", "n", "0"])

    # User login account
    USER_COOKIE = "publications_user"
    API_KEY_HEADERS = ["X-API-key", "X-Publications-API-key"]

    # Content types (MIME types)
    HTML_MIME = "text/html"
    JSON_MIME = "application/json"
    CSV_MIME = "text/csv"
    XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    TXT_MIME = "text/plain"
    PNG_MIME = "image/png"

    # Various texts.
    REV_ERROR = "Entity has been edited by someone else. Cannot overwrite."
    FETCH_ERROR = "Could not fetch data. "
    BLACKLISTED_MESSAGE = (
        "Publication(s) not fetched since it is in the blacklist."
        " Check 'override' and try again, if needed: "
    )

    # Hard-wired URL templates for the most important external sites.
    PUBMED_URL = "https://pubmed.ncbi.nlm.nih.gov/%s/"
    DOI_URL = "https://doi.org/%s"
    ORCID_URL = "https://orcid.org/%s"
    CROSSREF_URL = "https://search.crossref.org/?q=%s"

    IDENTIFIER_PREFIXES = [
        "doi:",
        "pmid:",
        "pubmed:",
        "http://doi.org/",
        "https://doi.org/",
        "http://dx.doi.org/",
    ]

    # Search setup; characters to remove and words to ignore.
    SEARCH_REMOVE = "-_\.:,?()'$"
    SEARCH_IGNORE = [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "but",
        "by",
        "can",
        "for",
        "from",
        "into",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "to",
        "using",
        "with",
    ]


constants = Constants()


# Loaded by 'config.load_settings_from_file' and 'config.load_settings_from_db'.
settings = dict()
