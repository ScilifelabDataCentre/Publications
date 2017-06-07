"Publication pages."

from __future__ import print_function

import logging
from collections import OrderedDict as OD

import requests
import tornado.web

from . import constants
from . import crossref
from . import pubmed
from . import settings
from . import utils
from .saver import Saver, SaverError
from .requesthandler import RequestHandler


FETCH_ERROR = 'Could not fetch article data: '
BLACKLISTED_MESSAGE = "Article data was not fetched since it is in the" \
                      " blacklist. Check 'override' if desired."


class PublicationSaver(Saver):
    doctype = constants.PUBLICATION

    def check_published(self, value):
        utils.to_date(value)

    def convert_published(self, value):
        return utils.to_date(value)

    def check_epublished(self, value):
        utils.to_date(value)

    def convert_epublished(self, value):
        if value:
            return utils.to_date(value)
        else:
            return None

    def set_title(self):
        "Set title from form data."
        assert self.rqh, 'requires http request context'
        self['title'] = self.rqh.get_argument('title', '') or '[no title]'

    def set_authors(self):
        "Set authors list from form data."
        assert self.rqh, 'requires http request context'
        authors = []
        for author in self.rqh.get_argument('authors', '').split('\n'):
            author = author.strip()
            if not author: continue
            try:
                family, given = author.split(',', 1)
            except ValueError:
                parts = author.split()
                family = parts[-1]
                given = ' '.join(parts[:-1])
            else:
                family = family.strip()
                if not family:
                    family = author
                    given = ''
                given = given.strip()
            initials = ''.join([c[0] for c in given.split()])
            authors.append(
                dict(family=family,
                     family_normalized=utils.to_ascii(family).lower(),
                     given=given,
                     given_normalized=utils.to_ascii(given).lower(),
                     initials=initials,
                     initials_normalized=utils.to_ascii(initials).lower()))
        self['authors'] = authors

    def set_pmid_doi(self):
        "Set pmid and doi from form data. No validity checks are made."
        assert self.rqh, 'requires http request context'
        self['pmid'] = self.rqh.get_argument('pmid', '') or None
        self['doi'] = self.rqh.get_argument('doi', '') or None

    def set_published(self):
        "Set published and epublished from form data."
        assert self.rqh, 'requires http request context'
        self['published'] = self.rqh.get_argument('published', '') or None
        self['epublished'] = self.rqh.get_argument('epublished','') or None

    def set_journal(self):
        "Set journal from form data."
        assert self.rqh, 'requires http request context'
        journal = dict(title=self.rqh.get_argument('journal', '') or None)
        for key in ['issn', 'volume', 'issue', 'pages']:
            journal[key] = self.rqh.get_argument(key, '') or None
        self['journal'] = journal

    def set_abstract(self):
        "Set abstract from form data."
        assert self.rqh, 'requires http request context'
        self['abstract'] = self.rqh.get_argument('abstract', '') or None

    def set_labels(self, allowed_labels):
        "Set labels from form data."
        assert self.rqh, 'requires http request context'
        self['labels'] = sorted(l for l in self.rqh.get_arguments('labels')
                                if l in allowed_labels)

    def fix_journal(self):
        """Set the appropriate journal title and ISSN if not done.
        Creates the journal entity if it does not exist."""
        assert self.rqh, 'requires http request context'
        journal = self['journal'].copy()
        issn = journal.get('issn')
        title = journal.get('title')
        if issn:
            try:
                doc = self.rqh.get_doc(issn, 'journal/issn')
            except KeyError:
                if title:
                    try:
                        doc = self.rqh.get_doc(title, 'journal/title')
                    except KeyError:
                        doc = None
                    else:
                        if issn != doc['issn']:
                            journal['issn'] = doc['issn']
                else:
                    doc = None
            else:
                if title != doc['title']:
                    journal['title'] = doc['title']
        self['journal'] = journal
        # Create journal entity if it does not exist, and if sufficient data.
        if doc is None and issn and title:
            # Done here to avoid circular import
            from publications.journal import JournalSaver
            with JournalSaver(db=self.db) as saver:
                saver['issn'] = issn
                saver['title'] = title


class PublicationMixin(object):
    "Mixin for access check methods."

    def is_editable(self, publication):
        "Is the publication editable by the current user?"
        return self.is_curator()

    def check_editable(self, publication):
        "Check that the publication is editable by the current user."
        if self.is_editable(publication): return
        raise ValueError('You many not edit the publication.')

    def is_deletable(self, publication):
        "Is the publication deletable by the current user?"
        return self.is_curator()

    def check_deletable(self, publication):
        "Check that the publication is deletable by the current user."
        if self.is_deletable(publication): return
        raise ValueError('You may not delete the publication.')

    def get_allowed_labels(self):
        "Get the set of allowed labels for the account."
        if self.is_admin():
            return set([l['value'] for l in self.get_docs('label/value')])
        else:
            return set(self.current_user['labels'])


class Publication(PublicationMixin, RequestHandler):
    "Display the publication."

    def get(self, identifier):
        "Display the publication."
        try:
            publication = self.get_publication(identifier)
        except KeyError, msg:
            self.see_other('home', error=str(msg))
            return
        self.render('publication.html',
                    publication=publication,
                    is_editable=self.is_editable(publication),
                    is_deletable=self.is_deletable(publication))

    def post(self, identifier):
        if self.get_argument('_http_method', None) == 'delete':
            self.delete(identifier)
            return
        raise tornado.web.HTTPError(405, reason='POST only allowed for DELETE')

    def delete(self, identifier):
        try:
            publication = self.get_publication(identifier)
            self.check_deletable(publication)
        except (KeyError, ValueError), msg:
            self.see_other('home', error=str(msg))
            return
        # Delete log entries
        for log in self.get_logs(publication['_id']):
            self.db.delete(log)
        self.db.delete(publication)
        self.see_other('home')


class PublicationJson(Publication):
    "Publication JSON data."

    def render(self, template, **kwargs):
        self.write(self.get_publication_json(kwargs['publication']))


class Publications(RequestHandler):
    "Publications list page."

    TEMPLATE = 'publications.html'

    def get(self, year=None):
        if year:
            publications = self.get_docs('publication/year', key=year)
            publications.sort(key=lambda i: i['published'], reverse=True)
        else:
            publications = self.get_docs('publication/published',
                                         key=constants.CEILING,
                                         last='',
                                         descending=True)
        self.render(self.TEMPLATE, publications=publications, year=year)


class PublicationsTable(Publications):
    "Publications table page."

    TEMPLATE = 'publications_table.html'


class PublicationsJson(Publications):
    "Publications JSON data."

    def render(self, template, **kwargs):
        URL = self.absolute_reverse_url
        publications = kwargs['publications']
        result = OD()
        result['entity'] = 'publications'
        result['timestamp'] = utils.timestamp()
        year = kwargs['year']
        if year:
            result['year'] = year
        result['links'] = links = OD()
        if year:
            links['self'] = {'href': URL('publications_year_json', year)}
            links['display'] = {'href': URL('publications_year', year)}
        else:
            links['self'] = {'href': URL('publications_json')}
            links['display'] = {'href': URL('publications')}
        result['publications_count'] = len(publications)
        result['publications'] = [self.get_publication_json(publication)
                                  for publication in publications]
        self.write(result)


class PublicationsUnverified(RequestHandler):
    """Unverified publications page.
    List according to which labels the account may use.
    """

    @tornado.web.authenticated
    def get(self):
        if self.is_admin():
            publications = self.get_docs('publication/unverified',
                                         descending=True)
        else:
            lookup = {}
            for label in self.current_user.get('labels'):
                docs = self.get_docs('publication/label_unverified',
                                     key=label)
                for doc in docs:
                    lookup[doc['_id']] = doc
            publications = lookup.values()
            publications.sort(key=lambda i: i['published'], reverse=True)
        self.render('publications_unverified.html', publications=publications)


class PublicationsNoPmid(RequestHandler):
    "Publications lacking PMID."

    def get(self):
        publications = self.get_docs('publication/no_pmid',
                                     descending=True)
        self.render('publications_no_pmid.html', publications=publications)


class PublicationsNoDoi(RequestHandler):
    "Publications lacking DOI."

    def get(self):
        publications = self.get_docs('publication/no_doi',
                                     descending=True)
        self.render('publications_no_doi.html', publications=publications)


class PublicationAdd(PublicationMixin, RequestHandler):
    "Add a publication by hand."

    def get(self):
        self.check_curator()
        self.render('publication_add.html', labels=self.get_allowed_labels())

    def post(self):
        self.check_curator()
        with PublicationSaver(rqh=self,account=self.current_user) as saver:
            saver.set_title()
            saver.set_authors()
            saver.set_published()
            saver.set_journal()
            saver.set_abstract()
            saver.set_labels(self.get_allowed_labels())
            # Publication should not be verified automatically by add!
            # It must be possible for admin to change labels in order to
            # challenge the relevant curators to verify or blacklist.
            publication = saver.doc
        self.see_other('publication', publication['_id'])


class PublicationFetch(RequestHandler):
    "Fetch a publication given its DOI or PMID."

    def get(self):
        self.check_curator()
        docs = self.get_docs('publication/modified',
                             key=constants.CEILING,
                             last=utils.today(-1),
                             descending=True,
                             limit=settings['SHORT_PUBLICATIONS_LIST_LIMIT'])
        self.render('publication_fetch.html',
                    publications=docs,
                    identifier=self.get_argument('identifier', ''))

    def post(self):
        self.check_curator()
        try:
            identifier = self.get_argument('identifier')
            identifier = utils.strip_prefix(identifier)
            if not identifier: raise ValueError
        except (tornado.web.MissingArgumentError, ValueError):
            self.see_other('publication_fetch')
            return
        # Check if identifier is present in blacklist registry
        override = utils.to_bool(self.get_argument('override', False))
        blacklisted = self.get_blacklisted(identifier)
        if blacklisted:
            if override:
                del self.db[blacklisted]
            else:
                self.see_other('publication_fetch',
                               identifier=identifier,
                               message=BLACKLISTED_MESSAGE)
                return
        # Has it already been fetched?
        try:
            old = self.get_publication(identifier, unverified=True)
        except KeyError:
            old = None
        if constants.PMID_RX.match(identifier):
            try:
                new = pubmed.fetch(identifier)
            except (IOError, requests.exceptions.Timeout), msg:
                self.see_other('publication_fetch',
                               error=FETCH_ERROR + str(msg))
                return
            else:
                if old is None:
                    # Maybe the publication has been loaded by DOI?
                    try:
                        old = self.get_publication(new.get('doi'))
                    except KeyError:
                        pass
        else:
            try:
                new = crossref.fetch(identifier)
            except (IOError, requests.exceptions.Timeout), msg:
                self.see_other('publication_fetch',
                               error=FETCH_ERROR + str(msg))
                return
            else:
                if old is None:
                    # Maybe the publication has been loaded by PMID?
                    try:
                        old = self.get_publication(new.get('pmid'))
                    except KeyError:
                        pass
        # Check blacklist registry again; the other external identifier maybe there
        for id in [new.get('pmid'), new.get('doi')]:
            if not id: continue
            blacklisted = self.get_blacklisted(id)
            if blacklisted:
                if override:
                    del self.db[blacklisted]
                else:
                    self.see_other('publication_fetch',
                                   identifier=identifier,
                                   message=BLACKLISTED_MESSAGE)
                    return
        if old:
            # Update everything
            with PublicationSaver(old, rqh=self) as saver:
                for key in new:
                    saver[key] = new[key]
                saver.fix_journal()
                if self.current_user['role'] == constants.CURATOR:
                    labels = set(old.get('labels', []))
                    labels.update(self.current_user['labels'])
                    saver['labels'] = sorted(labels)
                saver['verified'] = True
            publication = old
        else:
            with PublicationSaver(new, rqh=self) as saver:
                if self.current_user['role'] == constants.CURATOR:
                    saver['labels'] = sorted(self.current_user['labels'])
                else:
                    saver['labels'] = []
                saver.fix_journal()
                saver['verified'] = True
            publication = new
        self.see_other('publication_fetch')


class PublicationEdit(PublicationMixin, RequestHandler):
    "Edit the publication."

    def get(self, iuid):
        try:
            publication = self.get_publication(iuid)
            self.check_editable(publication)
        except (KeyError, ValueError), msg:
            self.see_other('home', error=str(msg))
            return
        self.render('publication_edit.html',
                    publication=publication,
                    labels=self.get_allowed_labels())

    def post(self, iuid):
        try:
            publication = self.get_publication(iuid)
            self.check_editable(publication)
        except (KeyError, ValueError), msg:
            self.see_other('home', error=str(msg))
            return
        try:
            with PublicationSaver(doc=publication, rqh=self) as saver:
                saver.check_revision()
                saver.set_title()
                saver.set_authors()
                saver.set_pmid_doi()
                saver.set_published()
                saver.set_journal()
                saver.set_abstract()
                saver.set_labels(self.get_allowed_labels())
                # Publication should not be verified automatically by edit!
                # It must be possible for admin to change labels in order to
                # challenge the relevant curators to verify or blacklist.
        except SaverError, msg:
            self.set_error_flash(utils.REV_ERROR)
        self.see_other('publication', publication['_id'])


class PublicationVerify(PublicationMixin, RequestHandler):
    "Verify publication."

    def post(self, identifier):
        self.check_curator()
        try:
            publication = self.get_publication(identifier)
        except KeyError, msg:
            self.see_other('home', error=str(msg))
            return
        with PublicationSaver(publication, rqh=self) as saver:
            saver['verified'] = True
        try:
            self.redirect(self.get_argument('next'))
        except tornado.web.MissingArgumentError:
            self.see_other('publication', publication['_id'])


class PublicationBlacklist(PublicationMixin, RequestHandler):
    "Blacklist a publication and record its external identifiers."

    def post(self, identifier):
        try:
            publication = self.get_publication(identifier)
            self.check_deletable(publication)
        except (KeyError, ValueError), msg:
            self.see_other('home', error=str(msg))
            return
        blacklist = {constants.DOCTYPE: constants.BLACKLIST,
                 'title': publication['title'],
                 'pmid': publication.get('pmid'),
                 'doi': publication.get('doi'),
                 'created': utils.timestamp(),
                 'owner': self.current_user['email']}
        self.db[utils.get_iuid()] = blacklist
        self.delete_entity(publication)
        try:
            self.redirect(self.get_argument('next'))
        except tornado.web.MissingArgumentError:
            self.see_other('home')
