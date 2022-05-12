"Publications: Login and logout pages."

import logging

import tornado.web

from publications import constants
from publications import settings
from publications import utils
from publications.requesthandler import RequestHandler
from publications.account import AccountSaver


class Login(RequestHandler):
    "Login to a account account. Set a secure cookie."

    def get(self):
        "Display login page."
        self.render("login.html")

    def post(self):
        """Login to a account account. Set a secure cookie.
        Log failed login attempt and disable account if too many recent.
        """
        try:
            email = self.get_argument("email")
            password = self.get_argument("password")
        except tornado.web.MissingArgumentError:
            self.set_error_flash("Missing email or password argument.")
            self.see_other("login")
            return
        try:
            account = self.get_account(email)
            if utils.hashed_password(password) != account.get("password"):
                raise KeyError
        except KeyError:
            self.set_error_flash("No such account or invalid password.")
            self.see_other("login")
        else:
            self.set_secure_cookie(
                constants.USER_COOKIE,
                account["email"],
                expires_days=settings["LOGIN_MAX_AGE_DAYS"],
            )
            with AccountSaver(doc=account, rqh=self) as saver:
                saver["login"] = utils.timestamp()  # Set last login timestamp.
            self.redirect(self.reverse_url("home"))


class Logout(RequestHandler):
    "Logout; unset the secure cookie to invalidate login session."

    @tornado.web.authenticated
    def post(self):
        self.set_secure_cookie(constants.USER_COOKIE, "")
        self.see_other("home")
