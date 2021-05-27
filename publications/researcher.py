"Researcher (person, but also possibly consortium or similar) pages."

import tornado.web

from . import constants
from . import settings
from . import utils
from .saver import Saver, SaverError
from .requesthandler import RequestHandler, ApiMixin


class ResearcherSaver(Saver):
    doctype = constants.RESEARCHER

    def set_family(self):
        "Set then family name from form data."
        assert self.rqh, "requires http request context"
        value = utils.squish(self.rqh.get_argument("family", ""))
        if not value:
            raise ValueError("No family name provided.")
        self["family"] = value
        self["family_normalized"] = utils.to_ascii(value).lower()

    def set_given(self):
        "Set the given name from form data."
        assert self.rqh, "requires http request context"
        value = utils.squish(self.rqh.get_argument("given", ""))
        self["given"] = value
        self["given_normalized"] = utils.to_ascii(value).lower()

    def set_initials(self):
        "Set the initials from form data."
        assert self.rqh, "requires http request context"
        value = "".join(self.rqh.get_argument("initials", "").split())
        self["initials"] = value
        self["initials_normalized"] = utils.to_ascii(value).lower()

    def set_orcid(self):
        "Set ORCID from form data."
        assert self.rqh, "requires http request context"
        self["orcid"] = utils.squish(self.rqh.get_argument("orcid", "")) or None

    def finalize(self):
        "Set the initials, in not done explicitly."
        super().finalize()
        if not self.get("initials"):
            value = "".join([n[0] for n in self.get("given", "").split() if n])
            self["initials"] = value
            self["initials_normalized"] = utils.to_ascii(value).lower()

    
class ResearcherMixin(object):
    "Mixin for access check methods."

    def get_researchers(self,  family, given=None, initials=None):
        """Get the researcher entities for the family name,
        optionally filtering by given name, and/or initials.
        Return a list of researcher documents.
        """
        family = utils.to_ascii(family).lower()
        result = self.get_docs("researcher/family", key=family)
        if given:
            given = utils.to_ascii(given).lower()
            result = [p for p in result 
                      if p["given_normalized"] == given]
        if initials:
            initials = utils.to_ascii(initials).lower()
            result = [p for p in result
                      if p["initials_normalized"].startswith(initials)]
        return result

    def is_editable(self, researcher):
        "Is the researcher editable by the current user?"
        return self.is_admin()

    def check_editable(self, researcher):
        "Raise ValueError if researcher is not editable."
        if self.is_editable(researcher): return
        raise ValueError("You may not edit the researcher.")

    def is_deletable(self, researcher):
        "Is the researcher deletable by the current user?"
        if not self.is_admin(): return False
        if self.get_docs("publication/researcher", key=researcher["_id"]):
            return False
        return True

    def check_deletable(self, journal):
        "Raise ValueError if researcher is not deletable."
        if self.is_deletable(journal): return
        raise ValueError("You may not delete the researcher.")


class Researcher(ResearcherMixin, RequestHandler):
    "Researcher page with list of publications."

    def get(self, identifier):
        "Display the researcher."
        try:
            researcher = self.get_researcher(identifier)
        except KeyError as error:
            self.see_other("home", error=str(error))
            return
        self.render("researcher.html",
                    researcher=researcher,
                    is_editable=self.is_editable(researcher),
                    is_deletable=self.is_deletable(researcher))

    @tornado.web.authenticated
    def post(self, identifier):
        if self.get_argument("_http_method", None) == "delete":
            self.delete(identifier)
            return
        raise tornado.web.HTTPError(405, reason="POST only allowed for DELETE")

    @tornado.web.authenticated
    def delete(self, identifier):
        try:
            researcher = self.get_researcher(identifier)
            self.check_deletable(researcher)
        except (KeyError, ValueError) as error:
            self.see_other("home", error=str(error))
            return
        # Delete log entries
        for log in self.get_logs(researcher["_id"]):
            self.db.delete(log)
        self.db.delete(researcher)
        self.see_other("home")


class ResearcherAdd(ResearcherMixin, RequestHandler):
    "Researcher addition page."

    @tornado.web.authenticated
    def get(self):
        self.check_admin()
        self.render("researcher_add.html")

    @tornado.web.authenticated
    def post(self):
        self.check_admin()
        try:
            with ResearcherSaver(rqh=self) as saver:
                saver.set_family()
                saver.set_given()
                saver.set_initials()
                saver.set_orcid()
                researcher = saver.doc
        except ValueError as error:
            self.set_error_flash(str(error))
            self.see_other("researcher_add")
            return
        self.see_other("researcher", researcher["_id"])


class ResearcherEdit(ResearcherMixin, RequestHandler):
    "Researcher edit page."

    @tornado.web.authenticated
    def get(self, identifier):
        try:
            researcher = self.get_researcher(identifier)
            self.check_editable(researcher)
        except (KeyError, ValueError) as error:
            self.see_other("home", error=str(error))
            return
        self.render("researcher_edit.html", researcher=researcher)

    @tornado.web.authenticated
    def post(self, identifier):
        try:
            researcher = self.get_researcher(identifier)
            self.check_editable(researcher)
        except (KeyError, ValueError) as error:
            self.see_other("home", error=str(error))
            return
        try:
            with ResearcherSaver(doc=researcher, rqh=self) as saver:
                saver.check_revision()
                saver.set_family()
                saver.set_given()
                saver.set_initials()
                saver.set_orcid()
        except ValueError as error:
            self.set_error_flash(str(error))
        except SaverError:
            self.set_error_flash(utils.REV_ERROR)
        self.see_other("researcher", researcher["_id"])


class Researchers(object):
    "Researchers list page."

    def get(self):
        researchers = self.get_docs("researcher/family")
        # XXX create template
        self.render("researchers.html", researchers=researchers)
