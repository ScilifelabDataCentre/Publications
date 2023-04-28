"Configuration of settings, and configuration pages."

import logging
import os
import os.path

import couchdb2
import tornado.web
import yaml

from publications import constants
from publications import settings
from publications.requesthandler import RequestHandler

import publications.saver


DEFAULT_SETTINGS = dict(
    SITE_DIR=os.path.normpath(os.path.join(constants.ROOT, "../site")),
    BASE_URL="http://localhost:8885/",
    PORT=8885,  # The port used by tornado.
    TORNADO_DEBUG=False,
    LOGGING_DEBUG=False,
    LOGGING_FORMAT="%(levelname)s [%(asctime)s] %(message)s",
    PIDFILE=None,
    DATABASE_SERVER="http://localhost:5984/",
    DATABASE_NAME="publications",
    DATABASE_ACCOUNT=None,  # Should probably be set to connect to CouchDB.
    DATABASE_PASSWORD=None,  # Should probably be set to connect to CouchDB.
    COOKIE_SECRET=None,  # Must be set!
    PASSWORD_SALT=None,  # Must be set!
    MAIL_SERVER=None,           # If not set, then no emails can be sent.
    MAIL_DEFAULT_SENDER=None,   # If not set, MAIL_USERNAME will be used.
    MAIL_PORT=25,
    MAIL_USE_SSL=False,
    MAIL_USE_TLS=False,
    MAIL_EHLO=None,
    MAIL_USERNAME=None,
    MAIL_PASSWORD=None,
    MAIL_REPLY_TO=None,
    MIN_PASSWORD_LENGTH=6,
    LOGIN_MAX_AGE_DAYS=14,
    PUBMED_DELAY=0.5,  # Delay before PubMed fetch, to avoid block.
    PUBMED_TIMEOUT=5.0,  # Timeout limit for PubMed fetch.
    NCBI_API_KEY=None,  # NCBI account API key, if any.
    CROSSREF_DELAY=0.5,  # Delay before Crossref fetch, to avoid block.
    CROSSREF_TIMEOUT=10.0,  # Timeout limit for Crossref fetch.
    PUBLICATIONS_FETCHED_LIMIT=10,
    SHORT_PUBLICATIONS_LIST_LIMIT=20,
    LONG_PUBLICATIONS_LIST_LIMIT=200,
    TEMPORAL_LABELS=False,
    FIRST_YEAR=2010,
    MAX_NUMBER_LABELS_PRECHECKED=6,
    NUMBER_FIRST_AUTHORS=3,
    NUMBER_LAST_AUTHORS=2,
    DISPLAY_TRANSLATIONS={},
    SITE_NAME="Publications",
    SITE_TITLE="Publications",
    SITE_TEXT="A publications reference database system.",
    SITE_PARENT_NAME="Site host",
    SITE_PARENT_URL=None,
    # XXX see MAIL_* variables?
    # SITE_EMAIL=None,            # Must be defined for email to work.
    # SITE_REPLY_TO_EMAIL=None,   # If not defined, uses SITE_EMAIL instead.
    SITE_CONTACT="<p><i>No contact information available.</i></p>",
    SITE_STATIC_DIR=os.path.normpath(os.path.join(constants.ROOT, "../site/static")),
    SITE_LABEL_QUALIFIERS=[],
    XREF_TEMPLATE_URLS={
        "ArrayExpress": "https://www.ebi.ac.uk/arrayexpress/experiments/%s/",
        "BioProject": "https://www.ncbi.nlm.nih.gov/bioproject/%s",
        "ClinicalTrials.gov": "https://clinicaltrials.gov/ct2/show/%s",
        "Dryad": "https://datadryad.org/resource/doi:%-s",
        "dbGaP": "https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=%-s",
        "EBI": "https://www.ebi.ac.uk/ebisearch/search.ebi?db=allebi&query=%s",
        "figshare": "https://doi.org/%s",
        "Genbank": "https://www.ncbi.nlm.nih.gov/nuccore/%s",
        "GEO": "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=%s",
        "ISRCTN": "https://doi.org/10.1186/%s",
        "Mendeley": "https://doi.org/%s",
        "mid": "https://www.ncbi.nlm.nih.gov/pubmed/?term=%s",
        "PDB": "https://www.rcsb.org/structure/%s/",
        "PMC": "https://www.ncbi.nlm.nih.gov/pmc/articles/%s/",
        "PubChem-Substance": "https://pubchem.ncbi.nlm.nih.gov/substance/%s",
        "RefSeq": "https://www.ncbi.nlm.nih.gov/nuccore/%s",
        "SRA": "https://www.ncbi.nlm.nih.gov/sra/?term=%s",
        "Zenodo": "https://doi.org/%s",
    },
)


def load_settings(filepath=None, log=True):
    """Load the settings. The file path first specified is used:
    1) The argument to this procedure (possibly from a command line argument).
    2) The environment variable PUBLICATIONS_SETTINGS_FILEPATH.
    3) The file '../site/settings.yaml' relative to this directory.
    If 'log' is True, activate logging according to DEBUG settings.
    Raise IOError if settings file could not be read.
    Raise KeyError if a settings variable is missing.
    Raise ValueError if a settings variable value is invalid.
    """
    settings.clear()
    settings.update(DEFAULT_SETTINGS)

    site_dir = settings["SITE_DIR"]
    if not os.path.exists(site_dir):
        raise IOError(f"The required site directory '{site_dir}' does not exist.")
    if not os.path.isdir(site_dir):
        raise IOError(f"The site directory path '{site_dir}' is not a directory.")
    # Find and read the settings file, updating the defaults.
    if not filepath:
        try:
            filename = os.environ["PUBLICATIONS_SETTINGS_FILEPATH"]
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
    if settings["MAIL_SERVER"] and not (settings["MAIL_DEFAULT_SENDER"] or settings["MAIL_USERNAME"]):
        raise ValueError("Either MAIL_DEFAULT_SENDER or MAIL_USERNAME must be defined.")

    # Set up the xref templates URLs; always lower-case keys.
    for key in list(settings["XREF_TEMPLATE_URLS"].keys()):
        settings["XREF_TEMPLATE_URLS"][key.lower()] = settings["XREF_TEMPLATE_URLS"].pop(key)
    settings["XREF_TEMPLATE_URLS"]["url"] = "%s"
