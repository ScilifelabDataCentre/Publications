"Configuration of settings, and configuration pages."

import logging
import os
import os.path

import couchdb2
import tornado.web
import yaml

from publications import constants
from publications import settings
from publications import utils
from publications.requesthandler import RequestHandler

import publications.saver


DEFAULT_SETTINGS = dict(
    BASE_URL="http://localhost:8885/",
    PORT=8885,  # The port used by tornado.
    TORNADO_DEBUG=False,
    LOGGING_DEBUG=False,
    DATABASE_SERVER="http://localhost:5984/",
    DATABASE_NAME="publications",
    DATABASE_ACCOUNT=None,  # Should probably be set to connect to CouchDB.
    DATABASE_PASSWORD=None,  # Should probably be set to connect to CouchDB.
    COOKIE_SECRET=None,  # Must be set!
    PASSWORD_SALT=None,  # Must be set!
    SETTINGS_FILEPATH=None,  # This value is set on startup.
    SETTINGS_ENVVAR=False,  # This value is set on startup.
    MAIL_SERVER=None,  # If not set, then no emails can be sent.
    MAIL_DEFAULT_SENDER=None,  # If not set, MAIL_USERNAME will be used.
    MAIL_PORT=25,
    MAIL_USE_SSL=False,
    MAIL_USE_TLS=False,
    MAIL_EHLO=None,
    MAIL_USERNAME=None,
    MAIL_PASSWORD=None,
    MAIL_REPLY_TO=None,
    MIN_PASSWORD_LENGTH=6,
    LOGIN_MAX_AGE_DAYS=14,
    PUBMED_DELAY=0.5,  # Delay before PubMed fetch, to avoid being blocked.
    PUBMED_TIMEOUT=5.0,  # Timeout limit for PubMed fetch.
    NCBI_API_KEY=None,  # NCBI account API key, if any.
    CROSSREF_DELAY=0.5,  # Delay before Crossref fetch, to avoid being blocked.
    CROSSREF_TIMEOUT=10.0,  # Timeout limit for Crossref fetch.
    PUBLICATIONS_FETCHED_LIMIT=10,
    MAX_NUMBER_LABELS_PRECHECKED=6,
)

SECRET_SETTINGS = (
    "PASSWORD_SALT",
    "COOKIE_SECRET",
    "DATABASE_PASSWORD",
    "MAIL_PASSWORD",
)


def load_settings_from_file():
    """Load the settings that are not stored in the database from file or
    environment variables.
    1) Initialize with the values in DEFAULT_SETTINGS.
    2) Try the filepath in the environment variable PUBLICATIONS_SETTINGS_FILEPATH.
    3) The file '../site/settings.yaml' relative to this directory.
    4) Use any environment variables defined; settings file values are overwritten.
    Raise KeyError if a settings variable is missing.
    Raise ValueError if a settings variable value is invalid.
    """
    settings.clear()
    settings.update(DEFAULT_SETTINGS)

    # Find and read the settings file, updating the defaults.
    try:
        filepath = os.environ["PUBLICATIONS_SETTINGS_FILEPATH"]
    except KeyError:
        filepath = os.path.join(constants.SITE_DIR, "settings.yaml")
    try:
        with open(filepath) as infile:
            from_settings_file = yaml.safe_load(infile)
    except OSError:
        obsolete_keys = []
    else:
        settings.update(from_settings_file)
        settings["SETTINGS_FILEPATH"] = filepath
        obsolete_keys = set(from_settings_file.keys()).difference(DEFAULT_SETTINGS)

    # Modify the settings from environment variables; convert to correct type.
    envvar_keys = []
    for key, value in DEFAULT_SETTINGS.items():
        try:
            new = os.environ[key]
        except KeyError:
            pass
        else:  # Do NOT catch any exception! Means bad setup.
            if isinstance(value, int):
                settings[key] = int(new)
            elif isinstance(value, bool):
                settings[key] = utils.to_bool(new)
            else:
                settings[key] = new
            envvar_keys.append(key)
            settings["SETTINGS_ENVVAR"] = True

    # Setup logging.
    logging.basicConfig(format=constants.LOGGING_FORMAT)
    logger = logging.getLogger("publications")
    if settings.get("LOGGING_DEBUG"):
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    logger.info(f"OrderPortal version {constants.VERSION}")
    logger.info(f"ROOT_DIR: {constants.ROOT_DIR}")
    logger.info(f"settings: {settings['SETTINGS_FILEPATH']}")
    logger.info(f"logger debug: {settings['LOGGING_DEBUG']}")
    logger.info(f"tornado debug: {settings['TORNADO_DEBUG']}")

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
    if settings["MAIL_SERVER"] and not (
        settings["MAIL_DEFAULT_SENDER"] or settings["MAIL_USERNAME"]
    ):
        raise ValueError("Either MAIL_DEFAULT_SENDER or MAIL_USERNAME must be defined.")


def load_settings_from_database(db):
    """Load settings from the database configuration document.
    Create and initialize the configuration document if it does not exist.
    """
    try:
        configuration = db["configuration"]
    except couchdb2.NotFoundError:
        configuration = {
            constants.DOCTYPE: constants.META,
            "_id": "configuration",
            "SITE_NAME": "Publications",
            "SITE_TEXT": "A publications reference database system.",
            "SITE_HOST_NAME": None,
            "SITE_HOST_URL": None,
            "SITE_CONTACT": None,
            "SITE_LABEL_QUALIFIERS": [],
        }
        db.put(configuration)
        logging.getLogger("publications").info("Created 'configuration' document.")

    # From version 9.2.0: Update from current 'settings', or set from scratch.
    if "DISPLAY_TRANSLATIONS" not in configuration:
        configuration["DISPLAY_TRANSLATIONS"]= {
            "label": settings["DISPLAY_TRANSLATIONS"].get("label"),
            "labels": settings["DISPLAY_TRANSLATIONS"].get("labels"),
        }
        configuration["TEMPORAL_LABELS"] = bool(settings.get("TEMPORAL_LABELS"))
        configuration["SHORT_PUBLICATIONS_LIST_LIMIT"] = 20
        configuration["LONG_PUBLICATIONS_LIST_LIMIT"] = 200
        configuration["NUMBER_FIRST_AUTHORS"] = 3
        configuration["NUMBER_LAST_AUTHORS"] = 2
        configuration["XREF_TEMPLATE_URLS"] = {  # Key is always lower-case.
            "url": "%s",
            "arrayexpress": "https://www.ebi.ac.uk/arrayexpress/experiments/%s/",
            "bioproject": "https://www.ncbi.nlm.nih.gov/bioproject/%s",
            "clinicaltrials.gov": "https://clinicaltrials.gov/ct2/show/%s",
            "dryad": "https://datadryad.org/resource/doi:%s",
            "dbgap": "https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=%-s",
            "ebi": "https://www.ebi.ac.uk/ebisearch/search.ebi?db=allebi&query=%s",
            "figshare": "https://doi.org/%s",
            "genbank": "https://www.ncbi.nlm.nih.gov/nuccore/%s",
            "geo": "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=%s",
            "isrctn": "https://doi.org/10.1186/%s",
            "mendeley": "https://doi.org/%s",
            "mid": "https://www.ncbi.nlm.nih.gov/pubmed/?term=%s",
            "pdb": "https://www.rcsb.org/structure/%s/",
            "pmc": "https://www.ncbi.nlm.nih.gov/pmc/articles/%s/",
            "pubchem-substance": "https://pubchem.ncbi.nlm.nih.gov/substance/%s",
            "refseq": "https://www.ncbi.nlm.nih.gov/nuccore/%s",
            "sra": "https://www.ncbi.nlm.nih.gov/sra/?term=%s",
            "zenodo": "https://doi.org/%s",
        }
        db.put(configuration)
        logging.getLogger("publications").info("Updated 'configuration' document.")

    settings.update(configuration)

    # Cache the image files directly in 'settings'.
    for name in ("icon", "favicon"):
        key = f"SITE_{name.upper()}"
        if configuration.get("_attachments", {}).get(name):
            settings[key] = dict(
                content_type=configuration["_attachments"][name]["content_type"],
                content=db.get_attachment(configuration, name).read(),
            )
        else:
            settings[key] = None


class Configuration(RequestHandler):
    "Configuration page."

    @tornado.web.authenticated
    def get(self):
        self.check_admin()
        self.render("configuration.html")

    @tornado.web.authenticated
    def post(self):
        self.check_admin()
        configuration = self.db["configuration"]
        try:
            configuration["SITE_NAME"] = self.get_argument("name") or "Publications"
            configuration["SITE_TEXT"] = (
                self.get_argument("text") or "A publications reference database system."
            )
            qualifiers = [
                q.strip() for q in self.get_argument("label_qualifiers", "").split("\n")
            ]
            configuration["SITE_LABEL_QUALIFIERS"] = [q for q in qualifiers if q]
            configuration["SITE_HOST_NAME"] = self.get_argument("host_name") or None
            configuration["SITE_HOST_URL"] = self.get_argument("host_url") or None
            for key in configuration["DISPLAY_TRANSLATIONS"]:
                value = self.get_argument(f"translation_{key}", "") or ""
                configuration["DISPLAY_TRANSLATIONS"][key] = value.strip() or None
            configuration["TEMPORAL_LABELS"] = utils.to_bool(self.get_argument("temporal_labels", False))
            for key in ["NUMBER_FIRST_AUTHORS",
                        "NUMBER_LAST_AUTHORS",
                        "SHORT_PUBLICATIONS_LIST_LIMIT",
                        "LONG_PUBLICATIONS_LIST_LIMIT"]:
                try:
                    configuration[key] = max(1, int(self.get_argument(key.lower())))
                except (ValueError, TypeError):
                    pass
            for key in list(configuration["XREF_TEMPLATE_URLS"]):
                value = self.get_argument(f"xref_{key}", None)
                print(key, value)
                if not value:
                    configuration["XREF_TEMPLATE_URLS"].pop(key)
            key = self.get_argument(f"xref", "").strip()
            if key:
                print(key)
                value = self.get_argument(f"xreftemplate", "").strip()
                print(value)
                if value and "%s" in value:
                    configuration["XREF_TEMPLATE_URLS"][key.lower()] = value
            self.db.put(configuration)

            # Set or remove new image files.
            for name in ("icon", "favicon"):
                if utils.to_bool(self.get_argument(f"{name}_default", False)):
                    try:
                        self.db.delete_attachment(configuration, name)
                    except couchdb2.NotFoundError:
                        pass
                try:
                    infile = self.request.files[name][0]
                except (KeyError, IndexError):
                    pass
                else:
                    self.db.put_attachment(
                        configuration, infile.body, name, infile.content_type
                    )
        except ValueError as error:
            self.set_error_flash(str(error))
        load_settings_from_database(self.db)
        self.see_other("configuration")
        return


class Site(RequestHandler):
    "Return a site-specific image file."

    def get(self, name):
        if name not in ("icon", "favicon"):
            raise tornado.web.HTTPError(404)
        data = settings[f"SITE_{name.upper()}"]
        if data is None:        # No file in database; use default.
            with open(f"{constants.STATIC_DIR}/{name}.png", "rb") as infile:
                data = dict(content=infile.read(), content_type=constants.PNG_MIME)
        self.write(data["content"])
        self.set_header("Content-Type", data["content_type"])
