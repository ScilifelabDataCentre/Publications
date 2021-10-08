"Logs page."

import logging

import couchdb2
import tornado.web

from publications import constants
from publications.requesthandler import RequestHandler


class Logs(RequestHandler):
    "Logs page."

    @tornado.web.authenticated
    def get(self, iuid):
        try:
            doc = self.db[iuid]
        except couchdb2.NotFoundError:
            raise tornado.web.HTTPError(404, reason="No such entity.")
        if doc[constants.DOCTYPE] == constants.PUBLICATION:
            title = doc["title"]
            href = self.reverse_url("publication", doc["_id"])
        elif doc[constants.DOCTYPE] == constants.ACCOUNT:
            self.check_owner(doc)
            title = doc["email"]
            href = self.reverse_url("account", doc["email"])
        else:
            raise NotImplementedError
        self.render("logs.html",
                    title=title,
                    href=href,
                    logs=self.get_logs(doc["_id"]))
