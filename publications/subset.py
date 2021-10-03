"Subset (publication sets) pages."

import tornado

from . import constants
from . import settings
from . import utils
from .saver import Saver, SaverError
from .requesthandler import RequestHandler, ApiMixin


class SubsetSaver(Saver):
    doctype = constants.SUBSET

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
        "Set the subset to be viewable by all."
        self["public"] = True

    def set_private(self):
        "Set the subset to be viewable by an admin only."
        self["public"] = False


class SubsetMixin:
    "Mixin for access check methods."

    def is_viewable(self, subset):
        "Is the subset viewable by the current user?"
        if subset["public"]: return True
        if self.is_admin(): return True
        return False

    def check_viewable(self, subset):
        "Check that the subset is viewable by the current user."
        if self.is_viewable(subset): return
        raise ValueError("You many not view the subset.")

    def is_editable(self, subset):
        "Is the subset editable by the current user?"
        if self.is_admin(): return True
        return False

    def check_editable(self, subset):
        "Check that the subset is editable by the current user."
        if self.is_editable(subset): return
        raise ValueError("You many not edit the subset.")

    def is_deletable(self, subset):
        "Is the subset deletable by the current user?"
        if subset["public"]: return False
        if self.is_admin(): return True
        return False

    def check_deletable(self, subset):
        "Check that the subset is deletable by the current user."
        if self.is_deletable(subset): return
        raise ValueError("You may not delete the subset.")


class Subset(SubsetMixin, RequestHandler):
    "Display the subset."

    def get(self, identifier):
        "Display the publications in the subset."
        try:
            subset = self.get_subset(identifier)
            self.check_viewable(subset)
        except (KeyError, ValueError) as error:
            self.see_other("home", error=str(error))
            return
        # XXX Get publications documents.
        publications = []
        self.render("subset.html",
                    subset=subset,
                    publications=publications,
                    is_editable=self.is_editable(subset),
                    is_deletable=self.is_deletable(subset))

    @tornado.web.authenticated
    def post(self, identifier):
        if self.get_argument("_http_method", None) == "delete":
            self.delete(identifier)
            return
        raise tornado.web.HTTPError(405, reason="POST only allowed for DELETE")

    @tornado.web.authenticated
    def delete(self, identifier):
        try:
            subset = self.get_subset(identifier)
            self.check_deletable(subset)
        except (KeyError, ValueError) as error:
            self.see_other("home", error=str(error))
            return
        # Delete log entries
        for log in self.get_logs(subset["_id"]):
            self.db.delete(log)
        self.db.delete(subset)
        self.see_other("home")


class SubsetCreate(RequestHandler):
    "Create a new subset."

    @tornado.web.authenticated
    def get(self):
        self.check_admin()
        self.render("subset_create.html")

    @tornado.web.authenticated
    def post(self):
        self.check_admin()
        with SubsetSaver(rqh=self) as saver:
            saver["title"] = self.get_argument("title", "[no title]")
        self.see_other("subset", saver["_id"])


class SubsetEdit(SubsetMixin, RequestHandler):
    "View the subset operations and edit them."

    @tornado.web.authenticated
    def get(self, identifier):
        try:
            subset = self.get_subset(identifier)
            self.check_editable(subset)
        except (KeyError, ValueError) as error:
            self.see_other("home", error=str(error))
            return
        self.render("subset_edit.html", subset=subset)

    @tornado.web.authenticated
    def post(self, identifier):
        pass


class Subsets(RequestHandler):
    "Table of subsets."

    def get(self):
        if self.is_admin():
            subsets = self.get_docs("subset/public")
        else:
            subsets = self.get_docs("subset/public", key=True)
        self.render("subsets.html", subsets=subsets)
