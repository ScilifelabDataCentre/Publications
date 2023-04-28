"Blacklisted publications."

import logging

import tornado.web

from publications import constants
from publications import settings
from publications import utils
from publications.requesthandler import RequestHandler

import publications.publication


class Blacklist(publications.publication.PublicationMixin, RequestHandler):
    "Blacklist a specified publication."

    @tornado.web.authenticated
    def post(self, identifier):
        try:
            publication = self.get_publication(identifier)
            self.check_deletable(publication)
        except (KeyError, ValueError) as error:
            self.see_other("home", error=str(error))
            return
        blacklist = {
            constants.DOCTYPE: constants.BLACKLIST,
            "_id": utils.get_iuid(),
            "title": publication["title"],
            "pmid": publication.get("pmid"),
            "doi": publication.get("doi"),
            "created": utils.timestamp(),
            "owner": self.current_user["email"],
        }
        self.db.put(blacklist)
        self.delete_entity(publication)
        self.see_other("home")


class Blacklisted(RequestHandler):
    "Display list of blacklisted publications, and remove entry from it."

    @tornado.web.authenticated
    def get(self):
        blacklisted = dict([(d["_id"], d) for d in self.get_docs("blacklist", "doi")])
        blacklisted.update(
            dict([(d["_id"], d) for d in self.get_docs("blacklist", "pmid")])
        )
        self.render("blacklisted.html", blacklisted=blacklisted.values())

    @tornado.web.authenticated
    def post(self):
        try:
            doc = self.db[self.get_argument("remove")]
        except KeyError:
            pass
        else:
            self.db.delete(doc)
        self.see_other("blacklisted")
