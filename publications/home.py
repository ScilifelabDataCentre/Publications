"Home page, and a few other pages."

import logging
import sys

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
        docs = self.get_docs("publication", "first_published",
                             key=constants.CEILING,
                             last="",
                             descending=True,
                             limit=limit)
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
        v = sys.version_info
        self.render("software.html", software=[
            ("Publications", settings["SOURCE_VERSION"],settings["SOURCE_URL"]),
            ("Python", f"{v.major}.{v.minor}.{v.micro}", "https://www.python.org/"),
            ("tornado", tornado.version, "http://tornadoweb.org/"),
            ("certifi", certifi.__version__, "https://pypi.org/project/certifi/"),
            ("CouchDB server", self.db.server.version, "https://couchdb.apache.org/"),
            ("CouchDB2 interface", couchdb2.__version__, "https://pypi.org/project/couchdb2"),
            ("PyYAML", yaml.__version__, "https://pypi.org/project/PyYAML/"),
            ("pyparsing", pyparsing.__version__, "https://pyparsing-docs.readthedocs.io/"),
            ("requests", requests.__version__, "https://docs.python-requests.org/"),
            ("XlsxWriter", xlsxwriter.__version__, "https://pypi.org/project/XlsxWriter/"),
            ("Bootstrap", constants.BOOTSTRAP_VERSION, constants.BOOTSTRAP_URL),
            ("jQuery", constants.JQUERY_VERSION, constants.JQUERY_URL),
            ("DataTables", constants.DATATABLES_VERSION, constants.DATATABLES_URL),
        ])

class Status(RequestHandler):
    "Return JSON for the current status and some counts for the database."

    def get(self):
        self.write(dict(status="OK",
                        n_publications=self.get_count("publication", "year"),
                        n_labels=self.get_count("label", "value"),
                        n_researchers=self.get_count("researcher", "name")))


class Doc(RequestHandler):
    "Documentation page."

    def get(self, page):
        try:
            self.render(f"doc_{page}.html")
        except FileNotFoundError:
            self.set_error_flash("No such documentation page.")
            self.see_other("doc", "overview")
