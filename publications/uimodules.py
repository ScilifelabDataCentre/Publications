"Publications: User interface modules."

from __future__ import print_function

import tornado.web

from . import constants
from . import settings
from . import utils




class External(tornado.web.UIModule):
    "HTML for an external link."

    def render(self, key):
        if key:
            url = self.URL % key
            icon = '<img src="%s" class="logo-icon">' % self.handler.static_url(self.ICON)
            return '<p><a href="%s">%s %s</a></p>' % (url, icon, key)
        else:
            return ''

class Pubmed(External):
    "HTML for link to the PubMed item."
    URL = 'https://www.ncbi.nlm.nih.gov/pubmed/%s'
    ICON = 'pubmed_logo_100.png'
    

class Doi(External):
    "HTML for link to the DOI redirect service."
    URL = 'https://doi.org/%s'
    ICON = 'doi_logo_32.png'


class Crossref(External):
    "HTML for link to the Crossref service."
    URL = 'https://search.crossref.org/?q=%s'
    ICON = 'crossref-logo-landscape-100.png'
