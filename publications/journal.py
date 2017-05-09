"Journal pages."

from __future__ import print_function

import logging

import tornado.web

from . import constants
from . import settings
from . import utils
from .saver import Saver, SaverError
from .requesthandler import RequestHandler


class JournalSaver(Saver):
    doctype = constants.JOURNAL


class Journals(RequestHandler):
    "Journals table page."

    def get(self):
        journals = self.get_docs('journal/title')
        view = self.db.view('publication/issn', group=True)
        counts = dict([(r.key, r.value) for r in view])
        for journal in journals:
            journal['count'] = counts.get(journal.get('issn'), 0)
        self.render('journals.html', journals=journals)
