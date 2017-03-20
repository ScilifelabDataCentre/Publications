"Logs page."

import logging

import tornado.web

from . import constants
from .requesthandler import RequestHandler


class Logs(RequestHandler):
    "Logs page."

    @tornado.web.authenticated
    def get(self, iuid):
        self.check_admin()
        try:
            doc = self.get_doc(iuid)
        except KeyError:
            raise tornado.web.HTTPError(404, reason='No such entity.')
        if doc[constants.DOCTYPE] == constants.PUBLICATION:
            title = doc['title']
            href = self.reverse_url('publication', doc['_id'])
        elif doc[constants.DOCTYPE] == constants.ACCOUNT:
            title = doc['email']
            href = self.reverse_url('account', doc['email'])
        else:
            raise NotImplementedError("logs for %s" % doc[constants.DOCTYPE])
        self.render('logs.html',
                    title=title,
                    href=href,
                    logs=self.get_logs(iuid))
