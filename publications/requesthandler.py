"Publications: RequestHandler subclass."

import base64
import logging
import urllib

import couchdb
import tornado.web

import publications
from . import constants
from . import settings
from . import utils


class RequestHandler(tornado.web.RequestHandler):
    "Base request handler."

    def prepare(self):
        "Get the database connection."
        self.db = utils.get_db()

    def get_template_namespace(self):
        "Set the variables accessible within the template."
        result = super(RequestHandler, self).get_template_namespace()
        result['title'] = 'Publications'
        result['version'] = publications.__version__
        result['constants'] = constants
        result['settings'] = settings
        result['error'] = self.get_argument('error', None)
        result['message'] = self.get_argument('message', None)
        return result

    def see_other(self, name, *args, **query):
        """Redirect to the absolute URL given by name
        using HTTP status 303 See Other."""
        url = self.absolute_reverse_url(name, *args, **query)
        self.redirect(url, status=303)

    def absolute_reverse_url(self, name, *args, **query):
        "Get the absolute URL given the handler name, arguments and query."
        if name is None:
            path = ''
        else:
            path = self.reverse_url(name, *args, **query)
        return settings['BASE_URL'].rstrip('/') + path

    def reverse_url(self, name, *args, **query):
        "Allow adding query arguments to the URL."
        url = super(RequestHandler, self).reverse_url(name, *args)
        url = url.rstrip('?')   # tornado bug? sometimes left-over '?'
        if query:
            query = dict([(k, utils.to_utf8(v)) for k,v in query.items()])
            url += '?' + urllib.urlencode(query)
        return url

    def get_entity(self, iuid, doctype=None):
        """Get the entity by the IUID. Check the doctype, if given.
        Raise HTTP 404 if no such entity.
        """
        try:
            entity = self.db[iuid]
        except couchdb.ResourceNotFound:
            raise tornado.web.HTTPError(404, reason='Sorry, no such entity.')
        try:
            if doctype is not None and entity[constants.DOCTYPE] != doctype:
                raise KeyError
        except KeyError:
            raise tornado.web.HTTPError(
                404, reason='Internal problem: invalid entity doctype.')
        return entity

    def get_entity_view(self, viewname, key, reason='Sorry, no such entity.'):
        """Get the entity by the view name and the key.
        Raise HTTP 404 if no such entity.
        """
        view = self.db.view(viewname, include_docs=True)
        rows = list(view[key])
        if len(rows) == 1:
            return rows[0].doc
        else:
            raise tornado.web.HTTPError(404, reason=reason)

    def get_publication(self, identifier):
        """Get the publication given its DOI, PMID or IUID.
        Raise ValueError if no such publication.
        """
        try:
            return self.get_entity_view('publication/doi', identifier)
            return self.get_entity_view('publication/pmid', identifier)
        except tornado.web.HTTPError:
            raise ValueError('Sorry, no such publication.')

    def get_account(self, email):
        """Get the account identified by the email address.
        Raise ValueError if no such account.
        """
        try:
            return self.get_entity_view('account/email', email.strip().lower())
        except tornado.web.HTTPError:
            raise ValueError('Sorry, no such account.')

    def get_current_user(self):
        """Get the currently logged-in user account, if any.
        This overrides a tornado function, otherwise it should have
        been called 'get_current_account', since terminology 'account'
        is used in this code rather than 'user'."""
        try:
            account = self.get_current_user_session()
            if not account:
                account = self.get_current_user_basic()
            return account
        except ValueError:
            raise tornado.web.HTTPError(403)

    def get_current_user_session(self):
        """Get the current user from a secure login session cookie.
        Return None if no attempt at authentication.
        Raise ValueError if incorrect authentication."""
        email = self.get_secure_cookie(
            constants.USER_COOKIE,
            max_age_days=settings['LOGIN_MAX_AGE_DAYS'])
        if not email: return None
        account = self.get_account(email)
        # Check if login session is invalidated.
        if account.get('login') is None: raise ValueError
        logging.debug("Session login: account %s", account['email'])
        return account

    def get_current_user_basic(self):
        """Get the current user by HTTP Basic authentication.
        This should be used only if the site is using TLS (SSL, https).
        Return None if no attempt at authentication.
        Raise ValueError if incorrect authentication."""
        try:
            auth = self.request.headers['Authorization']
        except KeyError:
            return None
        try:
            auth = auth.split()
            if auth[0].lower() != 'basic': raise ValueError
            auth = base64.b64decode(auth[1])
            email, password = auth.split(':', 1)
            account = self.get_account(email)
            if utils.hashed_password(password) != account.get('password'):
                raise ValueError
        except (IndexError, ValueError, TypeError):
            raise ValueError
        logging.info("Basic auth login: account %s", account['email'])
        return account

    def is_admin(self):
        "Does the current user have 'admin' role?"
        return bool(self.current_user) and \
               self.current_user['role'] == constants.ADMIN

    def check_admin(self):
        "Check that the current user has 'admin' role."
        if not self.is_admin():
            raise tornado.web.HTTPError(403, reason="Role 'admin' required")

