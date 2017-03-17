"Publications: Publication pages."

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
        self.render('publication.html',
                    title=publication['title'],
                    publication=publication)


class PublicationAdd(RequestHandler):
    "Fetch a publication given its DOI or PMID and add it."

    @tornado.web.authenticated
    def get(self):
        self.check_admin()
        docs = self.get_docs('publication/created',
                             '9999', last='0', descending=True,
                             limit=settings['MOST_RECENT_LIMIT'])
        self.render('publication_add.html',
                    title='Add publication',
                    publications=docs)

    @tornado.web.authenticated
    def post(self):
        self.check_admin()
        try:
            identifier = self.get_argument('identifier')
            identifier = identifier.strip()
            if not identifier: raise ValueError
        except (tornado.web.MissingArgumentError, ValueError):
            self.see_other('publication_add', error='No identifier given.')
        try:
            publication = self.get_publication(identifier)
        except ValueError:
            if constants.PMID_RX.match(identifier):
                try:
                    publication = pubmed.fetch(identifier)
                except (IOError, requests.exceptions.Timeout):
                    self.see_other('publication_add',
                                   error='could not fetch article')
            else:
                try:
                    publication = crossref.fetch(identifier)
                except (IOError, requests.exceptions.Timeout):
                    self.see_other('publication_add',
                                   error='could not fetch article')
            with PublicationSaver(publication, rqh=self):
                pass
        self.see_other('publication_add')
        # self.see_other('publication', publication['_id'])
