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
            result = ['-']
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


class Xref(tornado.web.UIModule):
    "HTML for an external database entry other then PubMed, DOI or Crossref."

    ICON = '<span class="glyphicon glyphicon-share"></span>'

    def render(self, xref):
        try:
            href = xref['href']
        except KeyError:
            return '<span class="text-info">%s %s: %s</span>' % \
                (self.ICON, xref['db'], xref['key'])
        else:
            return '<a href="%s" class="label label-info>%s %s: %s</a>' % \
                (href, self.ICON, xref['db'], xref['key'])


class ExternalLink(tornado.web.UIModule):
    "HTML for a link to an external publication site."

    ICON = '<span class="glyphicon glyphicon-link"></span>'
    NAME = None
    URL = None

    def render(self, key):
        if key:
            return '<a class="nobr margin-r1" target="_" href="%s">' \
                ' %s %s: %s</a>' % \
                (self.URL % key, self.ICON, self.NAME, key)
        else:
            return '<span class="nobr margin-r1">%s: -</span>' % self.NAME


class PubmedLink(ExternalLink):
    "HTML for a link to the PubMed item."
    NAME = 'PubMed'
    URL = constants.PUBMED_URL
    

class DoiLink(ExternalLink):
    "HTML for a link to the DOI redirect service."
    NAME = 'DOI'
    URL = constants.DOI_URL


class CrossrefLink(ExternalLink):
    "HTML for a link to the Crossref service."
    NAME = 'Crossref'
    URL = 'https://search.crossref.org/?q=%s'


class ExternalButton(tornado.web.UIModule):
    "HTML for an external publication button link."

    ICON = '<span class="glyphicon glyphicon-link"></span>'
    NAME = None
    URL = None

    def render(self, key):
        name = self.NAME or self.__class__.__name__
        if key:
            attrs = 'class="btn btn-default btn-block btn-xs left" role="button" target="_"'
            url = self.URL % key
            return '<a %s href="%s">%s %s</a>' % \
                (attrs, url, self.ICON, name)
        else:
            return ''

class PubmedButton(ExternalButton):
    "HTML for a button link to the PubMed item."
    NAME = 'PubMed'
    URL = constants.PUBMED_URL
    

class DoiButton(ExternalButton):
    "HTML for a button link to the DOI redirect service."
    NAME = 'DOI'
    URL = constants.DOI_URL


class CrossrefButton(ExternalButton):
    "HTML for a button link to the Crossref service."
    NAME = 'Crossref'
    URL = 'https://search.crossref.org/?q=%s'
