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
IGNORE = {
    'a': 1,
    'an': 1,
    'and': 1,
    'are': 1,
    'as': 1,
    'at': 1,
    'but': 1,
    'by': 1,
    'can': 1,
    'for': 1,
    'from': 1,
    'into': 1,
    'in': 1,
    'is': 1,
    'of': 1,
    'on': 1,
    'or': 1,
    'that': 1,
    'the': 1,
    'to': 1,
    'using': 1,
    'with': 1
    }


class Search(RequestHandler):
    "Search publications for authors or words in title."

    def get(self):
        terms = []
        for term in self.get_argument('terms', '').split():
            term = ''.join([c for c in term if c not in REMOVE])
            if term: terms.append(term)
        if terms:
            hits = dict()
            for viewname in ['publication/author',
                             'publication/title',
                             'publication/pmid',
                             'publication/doi',
                             'publication/published',
                             'publication/label_parts']:
                view = self.db.view(viewname)
                for term in terms:
                    name = utils.to_ascii(term)
                    for item in view[name : name + constants.CEILING]:
                        try:
                            hits[item.id] += 1
                        except KeyError:
                            hits[item.id] = 1
            publications = [self.get_publication(id) for id in hits]
            scores = [(hits[p['_id']], p['published'], p)
                      for p in publications]
            publications = [s[2] for s in sorted(scores, reverse=True)]
        else:
            publications = []
        self.render('search.html',
                    publications=publications,
                    terms=self.get_argument('terms', ''))
