"Publications: Home page."

import logging

from .requesthandler import RequestHandler


class Home(RequestHandler):
    "Home page."

    def get(self):
        self.render('home.html')
