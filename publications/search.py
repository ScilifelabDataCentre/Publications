"Search for terms in publications."

from __future__ import print_function

import logging
from collections import OrderedDict as OD

from publications import constants
from publications import settings
from publications import utils
from publications.requesthandler import RequestHandler

# Must be kept in sync with
#  designs/publication/views/title.js
#  designs/publication/views/notes.js
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
    """Search publications for terms in fields of publication docs:
    author, title, notes, pmid, doi, published, epublished, issn, journal,
    label_parts.
    """

    def get(self):
        terms = self.get_argument('terms', '')
        # The search term is quoted; consider a single phrase.
        if terms.startswith('"') and terms.endswith('"'):
            terms = [terms[1:-1]]
        # Split up into separate terms.
        else:
            # Remove DOI and PMID prefixes and lowercase.
            terms = [utils.strip_prefix(t)
                     for t in self.get_argument('terms', '').split()]
            terms = [t.lower() for t in terms if t]
        iuids = set()
        for viewname in [None,
                         'publication/doi',
                         'publication/published',
                         'publication/epublished',
                         'publication/issn',
                         'publication/journal']:
            iuids.update(self.search(viewname, terms))
        # Now remove set of insignificant characters.
        terms = [''.join([c for c in t if c not in REMOVE])
                 for t in terms]
        terms = [t for t in terms if t]
        for viewname in ['publication/author',
                         'publication/title',
                         'publication/notes',
                         'publication/pmid',
                         'publication/label_parts']:
            iuids.update(self.search(viewname, terms))
        publications = [self.get_publication(iuid) for iuid in iuids]
        publications.sort(key=lambda p: p['published'], reverse=True)
        self.render('search.html',
                    publications=publications,
                    terms=self.get_argument('terms', ''))

    def search(self, viewname, terms):
        "Search the given view using the terms. Return set of IUIDs."
        result = set()
        if viewname is None:
            # IUID of publicaton entry.
            for term in terms:
                if term in self.db:
                    result.add(term)
        else:
            view = self.db.view(viewname, reduce=False)
            for term in terms:
                if term in IGNORE: continue
                for item in view[term : term + constants.CEILING]:
                    result.add(item.id)
        return result


class SearchJson(Search):
    "Output search results in JSON."

    def render(self, template, **kwargs):
        URL = self.absolute_reverse_url
        publications = kwargs['publications']
        terms = kwargs['terms']
        result = OD()
        result['entity'] = 'publications search'
        result['timestamp'] = utils.timestamp()
        result['terms'] = terms
        result['links'] = links = OD()
        links['self'] = {'href': URL('search_json', terms=terms)}
        links['display'] = {'href': URL('search', terms=terms)}
        result['publications_count'] = len(publications)
        result['publications'] = [self.get_publication_json(publication)
                                  for publication in publications]
        self.write(result)
