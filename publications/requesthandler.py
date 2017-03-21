"RequestHandler subclass."

import base64
import json
import logging
import urllib

import couchdb
import tornado.web

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
        result['constants'] = constants
        result['settings'] = settings
        result['is_admin'] = self.is_admin()
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

    def get_doc(self, key, viewname=None):
        """Get the document with the given id, or from the view if given.
        Raise KeyError if not found.
        """
        if viewname is None:
            try:
                return self.db[key]
            except couchdb.ResourceNotFound:
                raise KeyError
        else:
            result = list(self.db.view(viewname, include_docs=True)[key])
            if len(result) != 1:
                raise KeyError
            return result[0].doc

    def get_docs(self, viewname, key, last=None, distinct=True, **kwargs):
        """Get the list of documents using the named view and
        the given key or interval."""
        view = self.db.view(viewname, include_docs=True, **kwargs)
        if key is None:
            iterator = view
        elif last is None:
            iterator = view[key]
        else:
            iterator = view[key:last]
        result = []
        lookup = set()
        for item in iterator:
            if distinct and item.id in lookup: continue
            result.append(item.doc)
            lookup.add(item.id)
        return result

    def get_publication(self, identifier):
        """Get the publication given its IUID, DOI or PMID.
        Raise KeyError if no such publication.
        """
        if not identifier:
            raise KeyError
        try:
            doc = self.get_doc(identifier)
        except KeyError:
            try:
                doc = self.get_doc(identifier, 'publication/doi')
            except KeyError:
                doc = self.get_doc(identifier, 'publication/pmid')
        if doc[constants.DOCTYPE] != constants.PUBLICATION:
            raise KeyError
        return doc

    def get_trashed(self, identifier):
        """Get the trash document id if the publication with
        the external identifier has been trashed.
        """
        for viewname in ['trash/doi', 'trash/pmid']:
            try:
                return list(self.db.view(viewname)[identifier])[0].id
            except IndexError:
                pass
        return None

    def get_account(self, email):
        """Get the account identified by the email address.
        Raise KeyError if no such account.
        """
        doc = self.get_doc(email.strip().lower(), 'account/email')
        if doc[constants.DOCTYPE] != constants.ACCOUNT:
            raise KeyError
        return doc

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
        except KeyError:
            return None

    def get_current_user_session(self):
        """Get the current user from a secure login session cookie.
        Return None if no attempt at authentication.
        Raise KeyError if invalid authentication."""
        email = self.get_secure_cookie(
            constants.USER_COOKIE,
            max_age_days=settings['LOGIN_MAX_AGE_DAYS'])
        if not email: return None
        account = self.get_account(email)
        # Check if login session is invalidated.
        if account.get('login') is None: raise KeyError
        logging.debug("Session login: account %s", account['email'])
        return account

    def get_current_user_basic(self):
        """Get the current user by HTTP Basic authentication.
        This should be used only if the site is using TLS (SSL, https).
        Return None if no attempt at authentication.
        Raise KeyError if incorrect authentication."""
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
            raise KeyError
        logging.info("Basic auth login: account %s", account['email'])
        return account

    def get_logs(self, iuid):
        "Get the log entries for the document with the given IUID."
        return self.get_docs('log/doc',
                             key=[iuid, constants.CEILING],
                             last=[iuid, ''],
                             descending=True)

    def is_admin(self):
        "Does the current user have the 'admin' role?"
        return bool(self.current_user) and \
               self.current_user['role'] == constants.ADMIN

    def check_admin(self):
        "Check that the current user has the 'admin' role."
        if self.is_admin(): return
        raise tornado.web.HTTPError(403, reason="Role 'admin' required")

    def is_curator(self):
        "Does the current user have the 'curator' or 'admin' role?"
        return bool(self.current_user) and \
               self.current_user['role'] in (constants.CURATOR, constants.ADMIN)
        
    def check_curator(self):
        "Check that the current user has the 'curator' or 'admin' role."
        if self.is_curator(): return
        raise tornado.web.HTTPError(403, reason="Role 'curator' required")

    def is_owner(self, doc):
        "Is the current user the owner of the document?"
        return bool(self.current_user) and \
               self.current_user['email'] == doc['owner']
