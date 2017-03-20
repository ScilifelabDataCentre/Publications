"Publication pages."

from __future__ import print_function

import logging

import tornado.web

from . import constants
from . import crossref
from . import pubmed
from . import settings
from .saver import Saver
from .requesthandler import RequestHandler

class PublicationSaver(Saver):
    doctype = constants.PUBLICATION


class Publication(RequestHandler):
    "Display the publication."

    def get(self, identifier):
        "Display the publication."
        try:
            publication = self.get_publication(identifier)
        except KeyError:
            raise tornado.web.HTTPError(404, reason='No such publication.')
        kwargs = dict(title=publication['title'],
                      publication=publication)
        if self.is_admin():
            kwargs['logs'] = self.get_logs(publication)
        self.render('publication.html', **kwargs)


class PublicationAdd(RequestHandler):
    "Fetch a publication given its DOI or PMID and add it."

    @tornado.web.authenticated
    def get(self):
        self.check_admin()
        docs = self.get_docs('publication/created',
                             key=constants.CEILING, last='', descending=True,
                             limit=settings['MOST_RECENT_LIMIT'])
        self.render('publication_add.html',
                    title='Add publication',
                    publications=docs)

    @tornado.web.authenticated
    def post(self):
        self.check_admin()
        try:
            identifier = self.get_argument('identifier')
            if not identifier: raise ValueError
        except (tornado.web.MissingArgumentError, ValueError):
            self.see_other('publication_add')
            return
        try:
            old = self.get_publication(identifier)
        except KeyError:
            old = None
        if constants.PMID_RX.match(identifier):
            try:
                new = pubmed.fetch(identifier)
            except (IOError, requests.exceptions.Timeout):
                self.see_other('publication_add',
                               error='could not fetch article')
            else:
                if old is None:
                    try:
                        old = self.get_publication(new.get('doi'))
                    except KeyError:
                        pass
        else:
            try:
                new = crossref.fetch(identifier)
            except (IOError, requests.exceptions.Timeout):
                self.see_other('publication_add',
                               error='could not fetch article')
            else:
                if old is None:
                    try:
                        old = self.get_publication(new.get('pmid'))
                    except KeyError:
                        pass
        if old:
            with PublicationSaver(old, rqh=self) as saver:
                for key in new:
                    saver[key] = new[key]
        else:
            with PublicationSaver(new, rqh=self):
                pass
        self.see_other('publication_add')
