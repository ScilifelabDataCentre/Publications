"Pubset (publication sets) pages."

import tornado

from . import constants
from . import settings
from . import utils
from .saver import Saver, SaverError
from .requesthandler import RequestHandler, ApiMixin


class PubsetSaver(Saver):
    doctype = constants.PUBSET

    def initialize(self):
        """Set the initial values for the new document.
        Create the slots with empty starting values;
        allows using 'update' for new instance.
        """
        super().initialize()
        self["title"] = ""
        self["public"] = False
        self["operations"] = []
        self["count"] = 0

    def set_title(self):
        "Set title from form data."
        assert self.rqh, "requires http request context"
        self["title"] = utils.squish(self.rqh.get_argument("title", "") or "[no title]")

    def set_public(self):
        "Set the pubset to be viewable by all."
        self["public"] = True

    def set_private(self):
        "Set the pubset to be viewable by an admin only."
        self["public"] = False


class PubsetMixin:
    "Mixin for access check methods."

    def is_viewable(self, pubset):
        "Is the pubset viewable by the current user?"
        if pubset["public"]: return True
        if self.is_admin(): return True
        return False

    def check_viewable(self, pubset):
        "Check that the pubset is viewable by the current user."
        if self.is_viewable(pubset): return
        raise ValueError("You many not view the pubset.")

    def is_editable(self, pubset):
        "Is the pubset editable by the current user?"
        if self.is_admin(): return True
        return False

    def check_editable(self, pubset):
        "Check that the pubset is editable by the current user."
        if self.is_editable(pubset): return
        raise ValueError("You many not edit the pubset.")

    def is_deletable(self, pubset):
        "Is the pubset deletable by the current user?"
        if pubset["public"]: return False
        if self.is_admin(): return True
        return False

    def check_deletable(self, pubset):
        "Check that the pubset is deletable by the current user."
        if self.is_deletable(pubset): return
        raise ValueError("You may not delete the pubset.")


class Pubset(PubsetMixin, RequestHandler):
    "Display the pubset."

    def get(self, identifier):
        "Display the publications in the pubset."
        try:
            pubset = self.get_pubset(identifier)
            self.check_viewable(pubset)
        except (KeyError, ValueError) as error:
            self.see_other("home", error=str(error))
            return
        # XXX Get publications documents.
        publications = []
        self.render("pubset.html",
                    pubset=pubset,
                    publications=publications,
                    is_editable=self.is_editable(pubset),
                    is_deletable=self.is_deletable(pubset))

    @tornado.web.authenticated
    def post(self, identifier):
        if self.get_argument("_http_method", None) == "delete":
            self.delete(identifier)
            return
        raise tornado.web.HTTPError(405, reason="POST only allowed for DELETE")

    @tornado.web.authenticated
    def delete(self, identifier):
        try:
            pubset = self.get_pubset(identifier)
            self.check_deletable(pubset)
        except (KeyError, ValueError) as error:
            self.see_other("home", error=str(error))
            return
        # Delete log entries
        for log in self.get_logs(pubset["_id"]):
            self.db.delete(log)
        self.db.delete(pubset)
        self.see_other("home")


class PubsetCreate(RequestHandler):
    "Create a new pubset."

    @tornado.web.authenticated
    def get(self):
        self.check_admin()
        self.render("pubset_create.html")

    @tornado.web.authenticated
    def post(self):
        self.check_admin()
        with PubsetSaver(rqh=self) as saver:
            saver["title"] = self.get_argument("title", "[no title]")
        self.see_other("pubset", saver["_id"])


class PubsetEdit(PubsetMixin, RequestHandler):
    "View the pubset operations and edit them."

    @tornado.web.authenticated
    def get(self, identifier):
        try:
            pubset = self.get_pubset(identifier)
            self.check_editable(pubset)
        except (KeyError, ValueError) as error:
            self.see_other("home", error=str(error))
            return
        self.render("pubset_edit.html", pubset=pubset)

    @tornado.web.authenticated
    def post(self, identifier):
        pass


class Pubsets(RequestHandler):
    "List the pubsets."

    def get(self):
        if self.is_admin():
            pubsets = self.get_docs("pubset/count")
        else:
            pubsets = self.get_docs("pubset/public", key=True)
        self.render("pubsets.html", pubsets=pubsets)
