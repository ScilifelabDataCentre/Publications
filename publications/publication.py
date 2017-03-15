"Publications: Publication pages."

import logging

import tornado.web

from . import constants
from . import pubmed
from .saver import Saver
from .requesthandler import RequestHandler

class PublicationSaver(Saver):
    doctype = constants.PUBLICATION


class Publication(RequestHandler):
    "Display the publication."

    def get(self, identifier):
        raise NotImplementedError


class PublicationAdd(RequestHandler):
    "Fetch a publication given its DOI or PMID and add it."

    @tornado.web.authenticated
    def get(self):
        self.check_admin()
        self.render('publication_add.html', title='Add publication')

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
                self.see_other('publication_add', error='DOI not implemented')
                return
            with PublicationSaver(publication, rqh=self):
                pass
        self.see_other('publication_add')
        # self.see_other('publication', publication['_id'])
