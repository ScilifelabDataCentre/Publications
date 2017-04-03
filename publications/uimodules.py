"User web interface modules."

from __future__ import print_function

import tornado.web

from . import constants
from . import settings
from . import utils


class Authors(tornado.web.UIModule):
    "HTML for authors list."

    def render(self, publication, full=False):
        return utils.get_formatted_authors(publication, full=full)


class Journal(tornado.web.UIModule):
    "HTML for authors list."

    def render(self, publication):
        return utils.get_formatted_journal(publication)


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
