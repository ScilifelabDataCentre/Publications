"Publications: Login and logout pages."

from __future__ import print_function

import logging

import tornado.web

from . import constants
from . import settings
from . import utils
from .requesthandler import RequestHandler
from .account import AccountSaver


class Login(RequestHandler):
    "Login to a account account. Set a secure cookie."

    def get(self):
        "Display login page."
        self.render('login.html',
                    next=self.get_argument('next', self.reverse_url('home')))

    def post(self):
        """Login to a account account. Set a secure cookie.
        Log failed login attempt and disable account if too many recent.
        """
        try:
            email = self.get_argument('email')
            password = self.get_argument('password')
        except tornado.web.MissingArgumentError:
            self.see_other('login', error='Missing email or password argument.')
            return
        try:
            account = self.get_account(email)
            if utils.hashed_password(password) != account.get('password'):
                raise KeyError
        except KeyError:
            self.see_other('login',
                           error='No such account or invalid password.')
        else:
            self.set_secure_cookie(constants.USER_COOKIE,
                                   account['email'],
                                   expires_days=settings['LOGIN_MAX_AGE_DAYS'])
            with AccountSaver(doc=account, rqh=self) as saver:
                saver['login'] = utils.timestamp() # Set last login timestamp.
            self.redirect(self.get_argument('next', self.reverse_url('home')))


class Logout(RequestHandler):
    "Logout; unset the secure cookie to invalidate login session."

    @tornado.web.authenticated
    def post(self):
        self.set_secure_cookie(constants.USER_COOKIE, '')
        self.see_other('home')
