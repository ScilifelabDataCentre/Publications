"Publications: Account and login pages."

import logging

import tornado.web

from . import constants
from . import settings
from . import utils
from .saver import Saver, SaverError
from .requesthandler import RequestHandler

ADD_TITLE = "A new account in the website %s"

ADD_TEXT = """An account %(email)s in the %(site)s website %(site_url)s has been created.

To set the password, go to %(link)s and provide it.

Or, go to %(url)s and fill in the one-time code %(code)s manually and provide your password.

/The %(site)s administrator.
"""

RESET_TEXT = """The password for your account %(email)s in the %(site)s website %(site_url)s has been reset.

To set a new password, go to %(link)s and provide your new password.

Or, go to %(url)s and fill in the one-time code %(code)s manually and provide your new password.

/The %(site)s administrator.
"""

ENABLED_TEXT = """Your account %(email)s in the %(site)s website %(site_url)s has been enabled.

To set a new password, go to %(link)s and provide your new password.

Or, go to %(url)s and fill in the one-time code %(code)s manually and provide your new password.

/The %(site)s administrator.
"""

EMAIL_ERROR = "Could not send email! Contact the administrator."


class AccountSaver(Saver):
    doctype = constants.ACCOUNT

    def set_email(self, email):
        assert self.get("email") is None # Email must not have been set.
        email = email.strip().lower()
        if not email: raise ValueError("No email given.")
        if not constants.EMAIL_RX.match(email):
            raise ValueError("Malformed email value.")
        if len(list(self.db.view("account/email", key=email))) > 0:
            raise ValueError("Email is already in use.")
        self["email"] = email

    def erase_password(self):
        self["password"] = None

    def set_password(self, new):
        utils.check_password(new)
        self["code"] = None
        # Bypass ordinary 'set'; avoid logging password.
        self.doc["password"] = utils.hashed_password(new)
        self.changed["password"] = "******"

    def reset_password(self):
        "Invalidate any previous password and set activation code."
        self.erase_password()
        self["code"] = utils.get_iuid()

    def renew_api_key(self):
        "Set a new API key."
        self["api_key"] = utils.get_iuid()


class AccountMixin:
    "Mixin with access check methods and some others."

    def is_readable(self, account):
        "Is the account readable by the current user?"
        if self.is_owner(account): return True
        if self.is_admin(): return True
        return False

    def check_readable(self, account):
        "Check that the account is readable by the current user."
        if self.is_readable(account): return
        raise ValueError("You may not read the account.")

    def is_editable(self, account):
        "Is the account editable by the current user?"
        if self.is_owner(account): return True
        if self.is_admin(): return True
        return False

    def check_editable(self, account):
        "Check that the account is editable by the current user."
        if self.is_editable(account): return
        raise ValueError("You may not edit the account.")

    def is_deletable(self, account):
        "Is the account deletable by the current user?"
        if not self.is_admin(): return False
        if not self.get_docs("log/account",
                             key=[account["email"]],
                             last=[account["email"], constants.CEILING],
                             limit=1): return True
        return False

    def check_deletable(self, account):
        "Check that the account is deletable by the current user."
        if self.is_deletable(account): return
        raise ValueError("You may not delete the account.")


class Account(AccountMixin, RequestHandler):
    "Account page."

    @tornado.web.authenticated
    def get(self, email):
        try:
            account = self.get_account(email)
            self.check_readable(account)
        except (KeyError, ValueError) as error:
            self.set_error_flash(str(error))
            self.see_other("home")
            return
        self.render("account.html",
                    account=account,
                    is_editable=self.is_editable(account),
                    is_deletable=self.is_deletable(account))

    @tornado.web.authenticated
    def post(self, email):
        if self.get_argument("_http_method", None) == "delete":
            self.delete(email)
            return
        raise tornado.web.HTTPError(405, reason="POST only allowed for DELETE")

    @tornado.web.authenticated
    def delete(self, email):
        try:
            account = self.get_account(email)
            self.check_deletable(account)
        except (KeyError, ValueError) as error:
            self.set_error_flash(str(error))
            self.see_other("accounts")
            return
        # Delete log entries
        for log in self.get_logs(account["_id"]):
            self.db.delete(log)
        self.db.delete(account)
        self.see_other("accounts")


class AccountJson(Account):
    "Account JSON data."

    def render(self, template, **kwargs):
        self.write(self.get_account_json(kwargs["account"], full=True))


class Accounts(RequestHandler):
    "List of accounts."

    @tornado.web.authenticated
    def get(self):
        self.check_admin()
        accounts = self.get_docs("account/email")
        self.render("accounts.html", accounts=accounts)


class AccountsJson(Accounts):
    "Accounts JSON data."

    def render(self, template, **kwargs):
        URL = self.absolute_reverse_url
        accounts = kwargs["accounts"]
        result = dict()
        result["entity"] = "accounts"
        result["timestamp"] = utils.timestamp()
        result["accounts_count"] = len(accounts)
        result["accounts"] = [self.get_account_json(account, full=True)
                                  for account in accounts]
        self.write(result)


class AccountAdd(RequestHandler):
    "Account addition page."

    @tornado.web.authenticated
    def get(self):
        self.check_admin()
        self.render("account_add.html",
                    all_labels=[l["value"] for l in
                                self.get_docs("label/value")])

    @tornado.web.authenticated
    def post(self):
        self.check_admin()
        try:
            email = self.get_argument("account")
        except tornado.web.MissingArgumentError:
            self.set_error_flash("No account email provided.")
            self.see_other("account_add")
            return
        try:
            account = self.get_account(email)
        except KeyError:
            pass
        else:
            self.set_error_flash("Account already exists.")
            self.see_other("account", account["email"])
            return
        role = self.get_argument("role", constants.CURATOR)
        if role not in constants.ROLES:
            role = constants.CURATOR
        try:
            with AccountSaver(rqh=self) as saver:
                saver.set_email(email)
                saver["owner"] = email
                saver["name"] = self.get_argument("name", None)
                saver["role"] = role
                labels = set([l["value"] for l in self.get_docs("label/value")])
                saver["labels"] = sorted(l for l in self.get_arguments("labels")
                                         if l in labels)
                saver.reset_password()
            account = saver.doc
        except ValueError as error:
            self.set_error_flash(str(error))
            self.see_other("account_add")
            return
        if self.get_argument("email", False):
            data = dict(site=settings["SITE_NAME"],
                        site_url=self.absolute_reverse_url("home"),
                        email=account["email"],
                        code=account["code"],
                        url=self.absolute_reverse_url("account_password"),
                        link=self.absolute_reverse_url("account_password",
                                                       account=account["email"],
                                                       code=account["code"]))
            try:
                server = utils.EmailServer()
            except ValueError:
                self.set_error_flash("Could not send email to user!")
            else:
                server.send(account["email"],
                            ADD_TITLE % settings["SITE_NAME"],
                            ADD_TEXT % data)
        self.see_other("account", email)


class AccountEdit(AccountMixin, RequestHandler):
    "Account edit page."

    @tornado.web.authenticated
    def get(self, email):
        try:
            account = self.get_account(email)
        except KeyError as error:
            self.set_error_flash(str(error))
            self.see_other("home")
            return
        try:
            self.check_editable(account)
        except ValueError as error:
            self.set_error_flash(str(error))
            self.see_other("account", account["email"])
            return
        if self.is_admin():
            self.render("account_edit.html",
                        account=account,
                        labels=[l["value"] for l in
                                self.get_docs("label/value")])
        else:
            self.render("account_edit.html", account=account)

    @tornado.web.authenticated
    def post(self, email):
        try:
            account = self.get_account(email)
        except KeyError as error:
            self.set_error_flash(str(error))
            self.see_other("home")
            return
        try:
            self.check_editable(account)
        except ValueError as error:
            self.set_error_flash(str(error))
            self.see_other("account", account["email"])
            return
        try:
            with AccountSaver(account, rqh=self) as saver:
                if self.is_admin():
                    saver["role"] = self.get_argument("role", account["role"])
                    labels = set([l["value"] for l in
                                  self.get_docs("label/value")])
                    saver["labels"] = sorted(l for l
                                             in self.get_arguments("labels")
                                             if l in labels)
                saver["name"] = self.get_argument("name", None)
                if self.get_argument("api_key", None):
                    saver.renew_api_key()
        except SaverError:
            self.set_error_flash(utils.REV_ERROR)
        self.see_other("account", account["email"])


class AccountReset(RequestHandler):
    "Reset the password of the account; send an email with the one-time code."

    def get(self):
        if self.is_admin():
            account = self.get_argument("account", self.current_user["email"])
        elif self.current_user:
            account = self.current_user["email"]
        else:
            account = None
        if settings["EMAIL"]["HOST"]:
            self.render("account_reset.html", account=account)
        else:
            self.set_error_flash("Cannot reset password since"
                                 " no email server configuration.")
            self.see_other("home")

    def post(self):
        try:
            email = self.get_argument("account")
        except tornado.web.MissingArgumentError:
            self.see_other("home")
            return
        try:
            account = self.get_account(email)
        except KeyError:
            self.see_other("home")
            return
        # Check if disabled
        if account.get("disabled"):
            if self.is_admin():
                self.set_error_flash("Account is disabled.")
            self.see_other("home")
            return
        with AccountSaver(account, rqh=self) as saver:
            saver.reset_password()
        data = dict(site=settings["SITE_NAME"],
                    site_url=self.absolute_reverse_url("home"),
                    email=account["email"],
                    code=account["code"],
                    url=self.absolute_reverse_url("account_password"),
                    link=self.absolute_reverse_url("account_password",
                                                   account=account["email"],
                                                   code=account["code"]))
        try:
            server = utils.EmailServer()
        except ValueError:
            self.set_error_flash(EMAIL_ERROR)
        else:
            server.send(account["email"],
                        f"Reset your password in website {settings['SITE_NAME']}",
                        RESET_TEXT % data)
        self.see_other("home")


class AccountPassword(RequestHandler):
    """Set the password of the account; requires a one-time code.
    The admin does not need the one-time code.
    """

    def get(self):
        self.render("account_password.html",
                    email=self.get_argument("account", ""),
                    code=self.get_argument("code", ""))

    def post(self):
        try:
            email = self.get_argument("account")
            password = self.get_argument("password")
            code = self.get_argument("code", "")
            account = self.get_account(email)
            if not self.is_admin() and code != account.get("code"):
                raise ValueError
            with AccountSaver(account, rqh=self) as saver:
                saver.set_password(password)
                # Login directly if not already logged in
                if not self.current_user:
                    self.set_secure_cookie(
                        constants.USER_COOKIE,
                        account["email"],
                        expires_days=settings["LOGIN_MAX_AGE_DAYS"])
                    saver["login"] = utils.timestamp()
        except (tornado.web.MissingArgumentError, KeyError, ValueError):
            self.set_error_flash("Missing or wrong data in field(s).")
            self.see_other("account_password")
        else:
            self.see_other("account", account["email"])


class AccountDisable(RequestHandler):
    "Disable the account. Password is not touched."

    @tornado.web.authenticated
    def post(self, email):
        if not self.is_admin():
            self.set_error_flash("Only admin may disable an account.")
            self.see_other("home")
            return
        try:
            account = self.get_account(email)
        except KeyError as error:
            self.set_error_flash(str(error))
            self.see_other("home")
            return
        if account == self.current_user:
            self.set_error_flash("May not disable self.")
            self.see_other("home")
            return
        with AccountSaver(account, rqh=self) as saver:
            saver["disabled"] = True
        self.see_other("account", email)


class AccountEnable(RequestHandler):
    "Enable the account, reset the password, and send email about it."

    @tornado.web.authenticated
    def post(self, email):
        if not self.is_admin():
            self.set_error_flash("Only admin may enable an account.")
            self.see_other("home")
            return
        try:
            account = self.get_account(email)
        except KeyError as error:
            self.set_error_flash(str(error))
            self.see_other("home")
            return
        with AccountSaver(account, rqh=self) as saver:
            del saver["disabled"]
            saver.reset_password()
        data = dict(site=settings["SITE_NAME"],
                    site_url=self.absolute_reverse_url("home"),
                    email=account["email"],
                    code=account["code"],
                    url=self.absolute_reverse_url("account_password"),
                    link=self.absolute_reverse_url("account_password",
                                                   account=account["email"],
                                                   code=account["code"]))
        try:
            server = utils.EmailServer()
        except ValueError:
            self.set_error_flash(EMAIL_ERROR)
        else:
            server.send(account["email"],
                        f"Enabled your account in website {settings['SITE_NAME']}",
                        ENABLED_TEXT % data)
        self.see_other("account", email)
