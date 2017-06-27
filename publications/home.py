"Home page."

from __future__ import print_function

import logging

from . import constants
from . import settings
from .requesthandler import RequestHandler


class Home(RequestHandler):
    "Home page."

    def get(self):
        docs = self.get_docs('publication/first_published',
                             key=constants.CEILING,
                             last='',
                             descending=True,
                             limit=settings['SHORT_PUBLICATIONS_LIST_LIMIT'])
        self.render('home.html', publications=docs)


class Howto(RequestHandler):
    "How-to page."

    def get(self):
        self.render('howto.html')

class Contact(RequestHandler):
    "Contact page."

    def get(self):
        self.render('contact.html', contact=settings['SITE_CONTACT'])
