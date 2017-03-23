"User web interface modules."

from __future__ import print_function

import tornado.web

from . import constants
from . import settings
from . import utils


class Authors(tornado.web.UIModule):
    "HTML for authors list."

    def render(self, publication, full=False):
        authors = publication['authors']
        if full or len(authors) <= 4:
            result = ["%s %s" % (a['family'], a['initials']) for a in authors]
        else:
            result = ["%s %s" % (a['family'], a['initials'])
                      for a in authors[:3]]
            result.append('...')
            a = authors[-1]
            result.append("%s %s" % (a['family'], a['initials']))
        return ', '.join(result)


class Journal(tornado.web.UIModule):
    "HTML for authors list."

    def render(self, publication):
        journal = publication['journal']
        return ' '.join([journal.get('title') or '-',
                         "<strong>%s</strong>" % (journal.get('volume') or '-'),
                         "(%s)" % (journal.get('issue') or '-'),
                         journal.get('pages') or '-'])


class External(tornado.web.UIModule):
    "HTML for an external link."

    NAME = None
    URL = None

    def render(self, key, full=False):
        name = self.NAME or self.__class__.__name__
        if key:
            url = self.URL % key
            if full:
                return '<a href="%s">%s:&nbsp;%s</a>' % (url, name, key)
            else:
                return '<a href="%s">%s</a>' % (url, name)
        elif full:
            return "%s:&nbsp-" % name
        else:
            return ''

class Pubmed(External):
    "HTML for link to the PubMed item."
    NAME = 'PubMed'
    URL = 'https://www.ncbi.nlm.nih.gov/pubmed/%s'
    

class Doi(External):
    "HTML for link to the DOI redirect service."
    NAME = 'DOI'
    URL = 'https://doi.org/%s'


class Crossref(External):
    "HTML for link to the Crossref service."
    URL = 'https://search.crossref.org/?q=%s'
