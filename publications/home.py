"Home page."

import logging

import tornado.web

from . import constants
from . import settings
from .requesthandler import RequestHandler


class Home(RequestHandler):
    "Home page."

    def get(self):
        limit = self.get_limit(settings["SHORT_PUBLICATIONS_LIST_LIMIT"])
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
        if "PASSWORD" in cleaned.get("EMAIL", {}):
            cleaned["EMAIL"]["PASSWORD"] = "****"
        self.render("settings.html", cleaned_settings=sorted(cleaned.items()))


class Status(RequestHandler):
    "Return JSON for the current status and some counts for the database."

    def get(self):
        self.write(dict(status="OK",
                        n_publications=self.get_count("publication/year"),
                        n_labels=self.get_count("label/value"),
                        n_researchers=self.get_count("researcher/name")))
