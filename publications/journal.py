"Journal pages."

from __future__ import print_function

import logging
from collections import OrderedDict as OD

import tornado.web

from . import constants
from . import settings
from . import utils
from .saver import Saver, SaverError
from .requesthandler import RequestHandler
from .publication import PublicationSaver


class JournalSaver(Saver):
    doctype = constants.JOURNAL


class JournalMixin(object):
    "Mixin for access check methods."

    def get_journal(self, title):
        """Get the journal given title or ISSN.
        Raise KeyError if no such journal.
        """
        try:
            return self.get_doc(title, 'journal/title')
        except KeyError:
            try:
                return self.get_doc(title, 'journal/issn')
            except KeyError:
                raise KeyError("No such journal '%s'" % title)

    def is_editable(self, journal):
        return self.is_admin()

    def check_editable(self, journal):
        "Raise ValueError if not editable."
        if self.is_editable(journal): return
        raise ValueError('You may not edit the journal.')

    def is_deletable(self, journal):
        if not self.is_admin(): return False
        if self.get_docs('publication/journal', key=journal['title']):
            return False
        return True

    def check_deletable(self, journal):
        if self.is_deletable(journal): return
        raise ValueError('You may not delete the journal.')


class Journal(JournalMixin, RequestHandler):
    "Journal page with list of articles."

    def get(self, title):
        try:
            journal = self.get_doc(title, 'journal/title')
        except KeyError:
            try:
                journal = self.get_doc(title, 'journal/issn')
            except KeyError:
                self.see_other('home', error='no such journal')
                return
            else:
                duplicates = self.get_docs('journal/title', key=title)
        else:
            duplicates = self.get_docs('journal/issn', key=journal['issn'])
        duplicates = [d for d in duplicates if d['_id'] != journal['_id']]
        publications = {}
        if journal['title']:
            view = self.db.view('publication/journal', reduce=False)
            for row in view[journal['title']]:
                try:
                    publications[row.id] += 1
                except KeyError:
                    publications[row.id] = 1
        if journal['issn']:
            view = self.db.view('publication/issn', reduce=False)
            for row in view[journal['issn']]:
                try:
                    publications[row.id] += 1
                except KeyError:
                    publications[row.id] = 1
        publications = [self.db[i] for i in publications]
        publications.sort(key=lambda p: p['published'], reverse=True)
        self.render('journal.html',
                    journal=journal,
                    is_editable=self.is_editable(journal),
                    is_deletable=self.is_deletable(journal),
                    publications=publications,
                    duplicates=duplicates)

    def post(self, title):
        if self.get_argument('_http_method', None) == 'delete':
            self.delete(title)
            return
        raise tornado.web.HTTPError(
            405, reason='Internal problem; POST only allowed for DELETE.')

    def delete(self, title):
        try:
            journal = self.get_doc(title, 'journal/title')
            self.check_deletable(journal)
        except (KeyError, ValueError), msg:
            self.see_other('journals', error=str(msg))
            return
        self.delete_entity(journal)
        self.see_other('journals')


class JournalJson(Journal):
    "Journal JSON data."

    def render(self, template, **kwargs):
        URL = self.absolute_reverse_url
        journal = kwargs['journal']
        publications = kwargs['publications']
        result = OD()
        result['entity'] = 'journal'
        result['iuid'] = journal['_id']
        result['title'] = journal['title']
        result['issn'] = journal.get('issn')
        result['timestamp'] = utils.timestamp()
        result['links'] = links = OD()
        links['self'] = {'href': URL('journal_json', journal['title'])}
        links['display'] = {'href': URL('journal', journal['title'])}
        result['publications_count'] = len(publications)
        result['publications'] = [self.get_publication_json(publication)
                                  for publication in publications]
        result['created'] = journal['created']
        result['modified'] = journal['modified']
        self.write(result)


class JournalEdit(JournalMixin, RequestHandler):
    "Edit the journal title or ISSN. Modifies affected publications."

    @tornado.web.authenticated
    def get(self, title):
        try:
            journal = self.get_journal(title)
            self.check_editable(journal)
        except (KeyError, ValueError), msg:
            self.see_other('journals', error=str(msg))
            return
        self.render('journal_edit.html',
                    is_editable=self.is_editable(journal),
                    is_deletable=self.is_deletable(journal),
                    journal=journal)

    def post(self, title):
        try:
            journal = self.get_journal(title)
            self.check_editable(journal)
        except (KeyError, ValueError), msg:
            self.see_other('journals', error=str(msg))
            return
        old_title = journal['title']
        old_issn = journal.get('issn')
        with JournalSaver(doc=journal, rqh=self) as saver:
            saver.check_revision()
            try:
                title = self.get_argument('title')
            except tornado.web.MissingArgumentError:
                self.set_error_flash('no title provided')
                self.see_other('journal')
                return
            saver['title'] = title
            saver['issn'] = issn = self.get_argument('issn', None) or None
        if old_title != title or old_issn != issn:
            view = self.db.view('publication/journal',
                                key=old_title,
                                include_docs=True,
                                reduce=False)
            for row in view:
                with PublicationSaver(doc=row.doc, rqh=self) as saver:
                    journal  = saver['journal'].copy()
                    journal['title'] = title
                    journal['issn'] = issn
                    saver['journal'] = journal
        self.see_other('journal', journal['title'])

    
class Journals(RequestHandler):
    "Journals table page."

    def get(self):
        journals = self.get_docs('journal/title')
        view = self.db.view('publication/journal', group=True)
        counts = dict([(r.key, r.value) for r in view])
        for journal in journals:
            journal['count'] = counts.get(journal['title'], 0)
        self.render('journals.html', journals=journals)


class JournalsJson(Journals):
    "JSON for journals."

    def render(self, template, **kwargs):
        URL = self.absolute_reverse_url
        journals = kwargs['journals']
        result = OD()
        result['entity'] = 'journals'
        result['timestamp'] = utils.timestamp()
        result['links'] = links = OD()
        links['self'] = {'href': URL('journals_json')}
        links['display'] = {'href': URL('journals')}
        result['journals_count'] = len(journals)
        result['journals'] = items = []
        for journal in journals:
            item = OD()
            item['title'] = journal['title']
            item['issn'] = journal.get('issn')
            item['publications_count'] = journal['count']
            item['links'] = links = OD()
            links['self'] = {'href': URL('journal_json', journal['title'])}
            links['display'] = {'href': URL('journal', journal['title'])}
            items.append(item)
        self.write(result)
