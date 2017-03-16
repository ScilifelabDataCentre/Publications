"Publications: Home page."

import logging

from . import settings
from .requesthandler import RequestHandler


class Home(RequestHandler):
    "Home page."

    def get(self):
        docs = self.get_docs('publication/published',
                             '9999', last='0', descending=True,
                             limit=settings['MOST_RECENT_LIMIT'])
        self.render('home.html', publications=docs)
