"Publication pages."

from __future__ import print_function

import logging

import tornado.web

from . import constants
from . import crossref
from . import pubmed
from . import settings
from . import utils
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


class PublicationEdit(RequestHandler):
    "Edit the publication."

    @tornado.web.authenticated
    def get(self, iuid):
        self.check_admin()
        try:
            publication = self.get_publication(iuid)
        except KeyError:
            raise tornado.web.HTTPError(404, reason='No such publication.')
        self.render('publication_edit.html',
                    title='Edit publication',
                    publication=publication)

    @tornado.web.authenticated
    def post(self, iuid):
        self.check_admin()
        try:
            publication = self.get_publication(iuid)
        except KeyError:
            raise tornado.web.HTTPError(404, reason='No such publication.')
        with PublicationSaver(doc=publication, rqh=self) as saver:
            saver['title'] = self.get_argument('title', '') or '[no title]'
            authors = []
            for author in self.get_argument('authors', '').split('\n'):
                author = author.strip()
                if not author: continue
                try:
                    family, given = author.split(',', 1)
                    family = family.strip()
                    if not family: raise IndexError
                    given = given.strip()
                except IndexError:
                    family = author
                    given = ''
                else:
                    initials = ''.join([c[0] for c in given.split()])
                    authors.append(
                        dict(family=family,
                             family_normalized=utils.to_ascii(family),
                             given=given,
                             given_normalized=utils.to_ascii(given),
                             initials=initials,
                             initials_normalized=utils.to_ascii(initials)))
            saver['authors'] = authors
            saver['pmid'] = self.get_argument('pmid', '') or None
            saver['doi'] = self.get_argument('doi', '') or None
            journal = dict(title=self.get_argument('journal', '') or None)
            for key in ['issn', 'volume', 'issue', 'pages']:
                journal[key] = self.get_argument(key, '') or None
            saver['journal'] = journal
            saver['abstract'] = self.get_argument('abstract', '') or None
        self.see_other('publication', iuid)
