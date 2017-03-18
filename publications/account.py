"Publications: Account and login pages."

from __future__ import print_function

import csv
import logging
from collections import OrderedDict as OD
from cStringIO import StringIO

import tornado.web

from . import constants
from . import settings
from . import utils
from .saver import Saver
from .requesthandler import RequestHandler


class AccountSaver(Saver):
    doctype = constants.ACCOUNT

    def set_email(self, email):
        assert self.get('email') is None # Email must not have been set.
        email = email.strip().lower()
        if not email: raise ValueError('No email given.')
        if not constants.EMAIL_RX.match(email):
            raise ValueError('Malformed email value.')
        if len(list(self.db.view('account/email', key=email))) > 0:
            raise ValueError('Email is already in use.')
        self['email'] = email

    def erase_password(self):
        self['password'] = None

    def set_password(self, new):
        utils.check_password(new)
        self['code'] = None
        # Bypass ordinary 'set'; avoid logging password, even if hashed.
        self.doc['password'] = utils.hashed_password(new)
        self.changed['password'] = '******'

    def reset_password(self):
        "Invalidate any previous password and set activation code."
        self.erase_password()
        self['code'] = utils.get_iuid()


class AccountMixin(object):
    "Mixin of various useful methods."

    def is_readable(self, account):
        "Is the account readable by the current user?"
        if self.is_owner(account): return True
        if self.is_admin(): return True
        return False

    def check_readable(self, account):
        "Check that the account is readable by the current user."
        if self.is_readable(account): return
        raise ValueError('You may not read the account.')

    def is_editable(self, account):
        "Is the account editable by the current user?"
        if self.is_owner(account): return True
        if self.is_admin(): return True
        return False

    def check_editable(self, account):
        "Check that the account is editable by the current user."
        if self.is_readable(account): return
        raise ValueError('You may not edit the account.')


class Account(AccountMixin, RequestHandler):
    "Account page."

    @tornado.web.authenticated
    def get(self, email):
        try:
            account = self.get_account(email)
            self.check_readable(account)
        except ValueError, msg:
            self.see_other('home', error=str(msg))
            return
        view = self.db.view('log/account',
                            startkey=[account['email'], constants.CEILING],
                            lastkey=[account['email']],
                            descending=True,
                            limit=1)
        self.render('account.html',
                    account=account)

class AccountLogs(AccountMixin, RequestHandler):
    "Account log entries page."

    @tornado.web.authenticated
    def get(self, email):
        try:
            account = self.get_account(email)
            self.check_readable(account)
        except ValueError, msg:
            self.see_other('home', error=str(msg))
            return
        self.render('logs.html',
                    entity=account,
                    logs=self.get_logs(account['_id']))


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
            self.see_other('login', error='Sorry, no such account or invalid password.')
        else:
            self.set_secure_cookie(constants.USER_COOKIE,
                                   account['email'],
                                   expires_days=settings['LOGIN_MAX_AGE_DAYS'])
            with AccountSaver(doc=account, rqh=self) as saver:
                saver['login'] = utils.timestamp() # Set last login timestamp.
            self.redirect(self.get_argument('next', self.reverse_url('home')))


class Logout(RequestHandler):
    "Logout; unset the secure cookie, and invalidate login session."

    @tornado.web.authenticated
    def post(self):
        self.set_secure_cookie(constants.USER_COOKIE, '')
        self.see_other('home')

