"Home page, and a few other pages."

import certifi
import couchdb2
import pyparsing
import requests
import tornado
import tornado.web
import yaml
import xlsxwriter

from publications import constants
from publications import settings
from publications.requesthandler import RequestHandler


class Home(RequestHandler):
    "Home page."

    def get(self):
        limit = settings["SHORT_PUBLICATIONS_LIST_LIMIT"]
        docs = self.get_docs(
            "publication",
            "first_published",
            key=constants.CEILING,
            last="",
            descending=True,
            limit=limit,
        )
        self.render("home.html", publications=docs, limit=limit)


class Contact(RequestHandler):
    "Contact page."

    def get(self):
        self.render("contact.html", contact=settings["SITE_CONTACT"])


class Settings(RequestHandler):
    "Settings page."

    @tornado.web.authenticated
    def get(self):
        self.check_admin()
        cleaned = settings.copy()
        for key in ["PASSWORD_SALT", "COOKIE_SECRET", "DATABASE_PASSWORD"]:
            if key in cleaned:
                cleaned[key] = "****"
        email = cleaned.get("EMAIL") or {}
        if "PASSWORD" in email:
            cleaned["EMAIL"]["PASSWORD"] = "****"
        self.render("settings.html", cleaned_settings=sorted(cleaned.items()))


class Software(RequestHandler):
    "Software version information."

    def get(self):
        software = [
            ("Publications", constants.VERSION, constants.URL),
            ("Python", constants.PYTHON_VERSION, constants.PYTHON_URL),
            ("tornado", tornado.version, constants.TORNADO_URL),
            ("certifi", certifi.__version__, constants.CERTIFI_URL),
            ("CouchDB server", self.db.server.version, constants.COUCHDB_URL),
            ("CouchDB2 interface", couchdb2.__version__, constants.COUCHDB2_URL),
            ("XslxWriter", xlsxwriter.__version__, constants.XLSXWRITER_URL),
            ("PyYAML", yaml.__version__, constants.PYYAML_URL),
            ("pyparsing", pyparsing.__version__, constants.PYPARSING_URL),
            ("requests", requests.__version__, constants.REQUESTS_URL),
            ("Bootstrap", constants.BOOTSTRAP_VERSION, constants.BOOTSTRAP_URL),
            ("jQuery", constants.JQUERY_VERSION, constants.JQUERY_URL),
            (
                "jQuery.localtime",
                constants.JQUERY_LOCALTIME_VERSION,
                constants.JQUERY_LOCALTIME_URL,
            ),
            ("DataTables", constants.DATATABLES_VERSION, constants.DATATABLES_URL),
        ]
        self.render("software.html", software=software)


class Status(RequestHandler):
    "Return JSON for the current status and some counts for the database."

    def get(self):
        self.write(
            dict(
                status="OK",
                n_publications=self.get_count("publication", "year"),
                n_labels=self.get_count("label", "value"),
                n_researchers=self.get_count("researcher", "name"),
            )
        )


class Doc(RequestHandler):
    "Documentation page."

    def get(self, page):
        try:
            self.render(f"doc_{page}.html")
        except FileNotFoundError:
            self.set_error_flash("No such documentation page.")
            self.see_other("doc", "overview")
