"Search in publications for title, authors, pmid, doi, published and labels."

from __future__ import print_function

import logging

from publications import constants
from publications import settings
from publications import utils
from publications.requesthandler import RequestHandler

# Must be kept in sync with
#  designs/publication/views/title.js
#  designs/publication/views/label_parts.js
REMOVE = set('-\.:,?()$')
IGNORE = set([
    'a',
    'an',
    'and',
    'are',
    'as',
    'at',
    'but',
    'by',
    'can',
    'for',
    'from',
    'into',
    'in',
    'is',
    'of',
    'on',
    'or',
    'that',
    'the',
    'to',
    'using',
    'with',
    ])


class Search(RequestHandler):
    "Search publications for authors or words in title."

    def get(self):
        self.hits = dict()
        terms = self.get_argument('terms', '')
        # The search term as a phrase.
        if terms.startswith('"') and terms.endswith('"'):
            self.terms = [terms[1:-1]]
        # Split up into separate terms.
        else:
            self.terms = []
            # Remove DOI and PMID prefixes.
            for term in self.get_argument('terms', '').split():
                term = utils.strip_prefix(term)
                if term: self.terms.append(term.lower())
        for viewname in ['publication/doi',
                         'publication/published',
                         'publication/issn',
                         'publication/journal']:
            self.search(viewname)
        # Now remove set of insignificant characters.
        terms = self.terms
        self.terms = []
        for term in terms:
            term = ''.join([c for c in term if c not in REMOVE])
            if term: self.terms.append(term)
        for viewname in ['publication/author',
                         'publication/title',
                         'publication/pmid',
                         'publication/label_parts']:
            self.search(viewname)
        publications = [self.get_publication(id) for id in self.hits]
        scores = [(self.hits[p['_id']], p['published'], p)
                  for p in publications]
        publications = [s[2] for s in sorted(scores, reverse=True)]
        self.render('search.html',
                    publications=publications,
                    terms=self.get_argument('terms', ''))

    def search(self, viewname):
        view = self.db.view(viewname, reduce=False)
        for term in self.terms:
            if term in IGNORE: continue
            for item in view[term : term + constants.CEILING]:
                try:
                    self.hits[item.id] += 1
                except KeyError:
                    self.hits[item.id] = 1
