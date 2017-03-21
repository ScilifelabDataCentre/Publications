"Publications: Account and login pages."

from __future__ import print_function

import logging

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
        # Bypass ordinary 'set'; avoid logging password.
        self.doc['password'] = utils.hashed_password(new)
        self.changed['password'] = '******'

    def reset_password(self):
        "Invalidate any previous password and set activation code."
        self.erase_password()
        self['code'] = utils.get_iuid()


class AccountMixin(object):
    "Mixin with access check methods."

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
        except (KeyError, ValueError), msg:
            self.see_other('home', error=str(msg))
            return
        self.render('account.html', account=account)


class AccountEdit(AccountMixin, RequestHandler):
    "Account edit page."

    @tornado.web.authenticated
    def get(self, email):
        try:
            account = self.get_account(email)
        except KeyError, msg:
            self.see_other('home', error=str(msg))
            return
        try:
            self.check_editable(account)
        except ValueError, msg:
            self.see_other('account', account['email'], error=str(msg))
            return
        self.render('account_edit.html', account=account)

    @tornado.web.authenticated
    def get(self, email):
        try:
            account = self.get_account(email)
        except KeyError, msg:
            self.see_other('home', error=str(msg))
            return
        try:
            self.check_editable(account)
        except ValueError, msg:
            self.see_other('account', account['email'], error=str(msg))
            return
        with AccountSaver(account, rqh=self) as saver:
            if self.is_admin():
                saver['role'] = self.get_argument('role', account['role'])
        self.see_other('account', account['email'])
        

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


class Accounts(RequestHandler):
    "List of accounts."

    @tornado.web.authenticated
    def get(self):
        self.check_admin()
        accounts = self.get_docs('account/email', key=None)
        self.render('accounts.html', accounts=accounts)
