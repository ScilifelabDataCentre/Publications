"Home page."

import logging

from . import constants
from . import settings
from .requesthandler import RequestHandler


class Home(RequestHandler):
    "Home page."

    def get(self):
        limit = self.get_limit(settings['SHORT_PUBLICATIONS_LIST_LIMIT'])
        docs = self.get_docs('publication/first_published',
                             key=constants.CEILING,
                             last='',
                             descending=True,
                             limit=limit)
        self.render('home.html', publications=docs, limit=limit)


class Contact(RequestHandler):
    "Contact page."

    def get(self):
        self.render('contact.html', contact=settings['SITE_CONTACT'])
