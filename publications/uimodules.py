"User web interface modules."

from __future__ import print_function

import tornado.web

from . import constants
from . import settings
from . import utils


class Authors(tornado.web.UIModule):
    "HTML for authors list."

    def render(self, publication):
        return utils.get_formatted_authors(publication['authors'])


class Journal(tornado.web.UIModule):
    "HTML for authors list."

    def render(self, publication):
        journal = publication['journal']
        title = journal.get('title')
        if title:
            url = self.handler.reverse_url('journal', title)
            result = ['<a href="%s">%s</a>' % (url, title)]
        else:
            ['-']
        result.append("<strong>%s</strong>" % (journal.get('volume') or '-'))
        result.append("(%s)" % (journal.get('issue') or '-'))
        result.append(journal.get('pages') or '-')
        return ' '.join(result)


class Published(tornado.web.UIModule):
    "Published date, and online, if present."

    def render(self, publication):
        result = publication['published']
        epub = publication.get('epublished')
        if epub:
            result += '; online ' + epub
        return "[%s]" % result


class External(tornado.web.UIModule):
    "HTML for an external link."

    NAME = None
    URL = None

    def render(self, key, full=False):
        name = self.NAME or self.__class__.__name__
        if key:
            if full:
                attrs = 'class="nobr margin10" target="_"'
            else:
                attrs = 'class="btn btn-default btn-block btn-xs left" role="button" target="_"'
            url = self.URL % key
            span = '<span class="glyphicon glyphicon-link"></span>'
            if full:
                return '<a %s href="%s">%s %s:&nbsp;%s</a>' % (attrs, url, span, name, key)
            else:
                return '<a %s href="%s">%s %s</a>' % (attrs, url, span, name)
        elif full:
            return "%s:&nbsp-" % name
        else:
            return ''

class Pubmed(External):
    "HTML for link to the PubMed item."
    NAME = 'PubMed'
    URL = constants.PUBMED_URL
    

class Doi(External):
    "HTML for link to the DOI redirect service."
    NAME = 'DOI'
    URL = constants.DOI_URL


class Crossref(External):
    "HTML for link to the Crossref service."
    URL = 'https://search.crossref.org/?q=%s'
