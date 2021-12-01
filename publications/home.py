"Home page, and a few other pages."

import logging

import tornado.web

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
