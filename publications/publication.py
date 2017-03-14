"Publications: Publication pages."

import logging

import tornado.web

from . import constants
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
            try:
                if constants.PMID_RX.match(identifier):
                    publication = self.fetch_pmid(identifier)
                else:
                    publication=self.fetch_doi(identifier)
            except ValueError, msg:
                self.see_other('publication_add', error=str(msg))
        else:
            self.see_other('publication', publication['_id'])
