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

    def post(self):
        """Login to a account account. Set a secure cookie.
        Log failed login attempt and disable account if too many recent.
        """
        try:
            email = self.get_argument('email')
            password = self.get_argument('password')
        except tornado.web.MissingArgumentError:
            self.see_other('home', error='Missing email or password argument.')
            return
        msg = 'Sorry, no such account or invalid password.'
        try:
            account = self.get_account(email)
        except ValueError, msg:
            self.see_other('home', error=str(msg))
            return
        if utils.hashed_password(password) != account.get('password'):
            utils.write_log(self.db, self, account,
                            changed=dict(login_failure=account['email']))
            view = self.db.view('log/login_failure',
                                startkey=[account['_id'], utils.timestamp(-1)],
                                endkey=[account['_id'], utils.timestamp()])
            if len(list(view)) > settings['LOGIN_MAX_FAILURES']:
                logging.warning("account %s has been disabled due to"
                                " too many login failures", account['email'])
                with AccountSaver(doc=account, rqh=self) as saver:
                    saver.erase_password()
                msg = 'Too many failed login attempts: Your account has been' \
                      ' disabled. You must contact the site administrators.'
                self.see_other('home', error=msg)
                return
        self.set_secure_cookie(constants.USER_COOKIE,
                               account['email'],
                               expires_days=settings['LOGIN_MAX_AGE_DAYS'])
        with AccountSaver(doc=account, rqh=self) as saver:
            saver['login'] = utils.timestamp() # Set last login timestamp.
        try:
            self.redirect(self.get_argument('uri'))
        except tornado.web.MissingArgumentError:
            self.see_other('home')


class Logout(RequestHandler):
    "Logout; unset the secure cookie, and invalidate login session."

    @tornado.web.authenticated
    def post(self):
        self.set_secure_cookie(constants.USER_COOKIE, '')
        self.see_other('home')

