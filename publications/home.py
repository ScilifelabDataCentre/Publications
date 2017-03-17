"Home page."

import logging

from . import constants
from . import settings
from .requesthandler import RequestHandler


class Home(RequestHandler):
    "Home page."

    def get(self):
        docs = self.get_docs('publication/published',
                             key=constants.CEILING, last='', descending=True,
                             limit=settings['MOST_RECENT_LIMIT'])
        self.render('home.html', publications=docs)
