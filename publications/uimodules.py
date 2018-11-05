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
    "HTML for a general external database entry."

    ICON = '<span class="glyphicon glyphicon-share"></span>'
    ATTRS = 'class="btn btn-info btn-xs" role="button" target="_"'

    def render(self, xref, full=False):
        try:
            url = xref['href']
        except KeyError:
            try:
                url = settings['XREF_TEMPLATE_URLS'][xref['db'].lower()]
            except KeyError:
                url = None
            else:
                url = url % xref['key']
        if url:
            result = '<a %s href="%s">%s %s</a>' % \
                     (self.ATTRS, url, self.ICON, xref['db'])
        else:
            result = '<button disabled %s>%s %s</button>' % \
                     (self.ATTRS, self.ICON, xref['db'])
        if full: result = '<p>' + result + ' ' + xref['key'] + '</p>'
        return result


class ExternalButton(tornado.web.UIModule):
    "HTML for a button to an external publication page."

    ICON = '<span class="glyphicon glyphicon-link"></span>'
    ATTRS = 'class="btn btn-default btn-xs" role="button" target="_"'
    NAME = None
    URL = None

    def render(self, key, full=False):
        assert self.NAME
        assert self.URL
        if key:
            url = self.URL % key
            result = '<a %s href="%s">%s %s</a>' % \
                     (self.ATTRS, url, self.ICON, self.NAME)
            if full: result = '<p>' + result + ' ' + key + '</p>'
            return result
        else:
            return ''

class PubmedButton(ExternalButton):
    NAME = 'PubMed'
    URL = constants.PUBMED_URL
    

class DoiButton(ExternalButton):
    NAME = 'DOI'
    URL = constants.DOI_URL


class CrossrefButton(ExternalButton):
    NAME = 'Crossref'
    URL = 'https://search.crossref.org/?q=%s'
