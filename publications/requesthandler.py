"RequestHandler subclass."

import base64
import json
import logging
import urllib.request, urllib.parse, urllib.error
from collections import OrderedDict as OD

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
        result['utils'] = utils
        result['is_admin'] = self.is_admin()
        result['is_curator'] = self.is_curator()
        result['error'] = self.get_cookie('error', '').replace('_', ' ')
        self.clear_cookie('error')
        result['message'] = self.get_cookie('message', '').replace('_', ' ')
        self.clear_cookie('message')
        result['year_counts'] = [(r.key, r.value) for r in 
                                 self.db.view('publication/year',
                                              descending=True,
                                              group_level=1)]
        return result

    def see_other(self, name, *args, **kwargs):
        """Redirect to the absolute URL given by name
        using HTTP status 303 See Other."""
        query = kwargs.copy()
        try:
            self.set_error_flash(query.pop('error'))
        except KeyError:
            pass
        try:
            self.set_message_flash(query.pop('message'))
        except KeyError:
            pass
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
        # Skip query arguments with None as value
        query = dict([(k, str(v)) for k,v in list(query.items())
                      if v is not None])
        if query:
            url += '?' + urllib.parse.urlencode(query)
        return url

    def set_message_flash(self, message):
        "Set message flash cookie."
        self.set_flash('message', message)

    def set_error_flash(self, message):
        "Set error flash cookie message."
        self.set_flash('error', message)

    def set_flash(self, name, message):
        message = message.replace(' ', '_')
        message = message.replace(';', '_')
        message = message.replace(',', '_')
        self.set_cookie(name, message)

    def get_doc(self, key, viewname=None):
        """Get the document with the given id, or from the given view.
        Raise KeyError if not found.
        """
        return utils.get_doc(self.db, key, viewname=viewname)

    def get_docs(self, viewname, key=None, last=None, **kwargs):
        """Get the list of documents using the named view
        and the given key or interval.
        """
        return utils.get_docs(self.db, viewname, key=key, last=last, **kwargs)

    def get_publication(self, identifier):
        """Get the publication given its IUID, DOI or PMID.
        Raise KeyError if no such publication.
        """
        return utils.get_publication(self.db, identifier)

    def get_label(self, identifier):
        """Get the label document by its IUID or value.
        Raise KeyError if no such publication.
        """
        return utils.get_label(self.db, identifier)

    def get_blacklisted(self, identifier):
        """Get the blacklist document id if the publication with
        the external identifier has been blacklisted.
        """
        return utils.get_blacklisted(self.db, identifier)

    def get_account(self, email):
        """Get the account identified by the email address.
        Raise KeyError if no such account.
        """
        return utils.get_account(self.db, email)

    def get_current_user(self):
        """Get the currently logged-in user account, or None.
        This overrides a tornado function, otherwise it should have
        been called 'get_current_account', since the term 'account'
        is used in this code rather than 'user'."""
        try:
            return self.get_current_user_api_key()
        except ValueError:
            try:
                return self.get_current_user_session()
            except ValueError:
                try:
                    return self.get_current_user_basic()
                except ValueError:
                    pass
        return None

    def get_current_user_api_key(self):
        """Get the current user by API key authentication.
        Raise ValueError if no or erroneous authentication.
        """
        try:
            api_key = self.request.headers[constants.API_KEY_HEADER]
        except KeyError:
            raise ValueError
        else:
            try:
                account = self.get_doc(api_key, 'account/api_key')
            except KeyError:
                raise ValueError
            if account.get('disabled'):
                logging.info("API key login: DISABLED %s",
                             account['email'])
                return None
            else:
                logging.info("API key login: %s", account['email'])
                return account

    def get_current_user_session(self):
        """Get the current user from a secure login session cookie.
        Raise ValueError if no or erroneous authentication.
        """
        email = self.get_secure_cookie(
            constants.USER_COOKIE,
            max_age_days=settings['LOGIN_MAX_AGE_DAYS'])
        if not email: raise ValueError
        email = email.decode('utf-8')
        try:
            account = self.get_account(email)
        except KeyError:
            return None
        # Check if login session is invalidated.
        if account.get('login') is None: raise ValueError
        if account.get('disabled'):
            logging.info("Session authentication: DISABLED %s",
                         account['email'])
            return None
        else:
            logging.info("Session authentication: %s", account['email'])
            return account

    def get_current_user_basic(self):
        """Get the current user by HTTP Basic authentication.
        This should be used only if the site is using TLS (SSL, https).
        Raise ValueError if no or erroneous authentication.
        """
        try:
            auth = self.request.headers['Authorization']
        except KeyError:
            raise ValueError
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
        if account.get('disabled'):
            logging.info("Basic auth login: DISABLED %s", account['email'])
            return None
        else:
            logging.info("Basic auth login: %s", account['email'])
            return account

    def get_limit(self, default=None):
        "Get the limit query argument, or the default value."
        try:
            limit = int(self.get_argument('limit'))
            if limit <= 0: raise ValueError
        except (tornado.web.MissingArgumentError, ValueError, TypeError):
            limit = default
        return limit

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
        raise tornado.web.HTTPError(403, reason="Role 'admin' required.")

    def is_curator(self):
        "Does the current user have the 'curator' or 'admin' role?"
        return bool(self.current_user) and \
               self.current_user['role'] in (constants.CURATOR, constants.ADMIN)
        
    def check_curator(self):
        "Check that the current user has the 'curator' or 'admin' role."
        if self.is_curator(): return
        raise tornado.web.HTTPError(403, reason="Role 'curator' required.")

    def is_xrefcur(self):
        """Does the current user have the 'xref-curator', 'curator' 
        or 'admin' role?"""
        return bool(self.current_user) and \
               self.current_user['role'] in (constants.XREFCUR, 
                                             constants.CURATOR,
                                             constants.ADMIN)
        
    def check_xrefcur(self):
        """Check that current user has the 'xrefcur', 'curator'
        or 'admin' role."""
        if self.is_xrefcur(): return
        raise tornado.web.HTTPError(403, reason="Role 'xref-curator' required.")

    def is_owner(self, doc):
        """Is the current user the owner of the document?
        Role 'admin' is also allowed."""
        return bool(self.current_user) and \
               (self.current_user['email'] == doc['owner'] or
                self.is_admin())

    def check_owner(self, doc):
        "Check that the current user is the owner of the document."
        if self.is_owner(doc): return
        raise tornado.web.HTTPError(403, reason="You are not the owner.")

    def delete_entity(self, doc):
        "Delete the entity and its log entries."
        assert constants.DOCTYPE in doc, 'doctype must be defined'
        assert doc[constants.DOCTYPE] in constants.ENTITIES, 'must be an entity'
        for log in self.get_logs(doc['_id']):
            self.db.delete(log)
        self.db.delete(doc)

    def get_publication_json(self, publication, full=True, single=False):
        "JSON representation of publication."
        URL = self.absolute_reverse_url
        result = OD()
        if full:
            result['entity'] = 'publication'
            result['iuid'] = publication['_id']
            if single:
                result['timestamp'] = utils.timestamp()
            result['links'] = OD([
                ('self', { 'href': URL('publication_json',publication['_id'])}),
                ('display', {'href': URL('publication', publication['_id'])})])
        result['title'] = publication['title']
        if full:
            result['authors'] = []
            for author in publication['authors']:
                au = OD()
                au['family'] = author.get('family')
                au['given'] = author.get('given')
                au['initials'] = author.get('initials')
                result['authors'].append(au)
            result['type'] = publication.get('type')
        result['published'] = publication.get('published')
        result['journal'] = publication.get('journal')
        if full:
            result['abstract'] = publication.get('abstract')
        result['doi'] = publication.get('doi')
        result['pmid'] = publication.get('pmid')
        result['labels'] = publication.get('labels') or []
        result['xrefs'] = publication.get('xrefs') or []
        if full:
            result['notes'] = publication.get('notes') or []
            result['qc'] = publication.get('qc')
            if self.current_user:
                try:
                    result['acquired'] = publication['acquired']
                except KeyError:
                    pass
            result['created'] = publication['created']
            result['modified'] = publication['modified']
        return result

    def get_account_json(self, account, full=False):
        "JSON representation of account."
        URL = self.absolute_reverse_url
        result = OD()
        result['entity'] = 'account'
        result['iuid'] = account['_id']
        result['timestamp'] = utils.timestamp()
        result['links'] = OD([
            ('self', { 'href': URL('account_json', account['email'])}),
            ('display', {'href': URL('account', account['email'])})])
        result['email'] = account['email']
        result['name'] = account['name']
        result['role'] = account['role']
        result['status'] = account.get('disabled') and 'disabled' or 'enabled'
        result['login'] = account.get('login')
        if full:
            result['api_key'] = account.get('api_key')
            result['labels'] = labels = []
            for label in account['labels']:
                links = OD()
                links['self'] = {'href': URL('label_json', label)}
                links['display'] = {'href': URL('label', label)}
                labels.append(OD([('value', label),
                                  ('links', links)]))
        result['created'] = account['created']
        result['modified'] = account['modified']
        return result

    def get_label_json(self, label, publications=None,accounts=None,limit=None):
        "JSON representation of label."
        URL = self.absolute_reverse_url
        result = OD()
        result['entity'] = 'label'
        result['iuid'] = label['_id']
        result['timestamp'] = utils.timestamp()
        result['links'] = links = OD()
        links['self'] = {'href': URL('label_json', label['value'])}
        links['display'] = {'href': URL('label', label['value'])}
        result['value'] = label['value']
        result['created'] = label['created']
        result['modified'] = label['modified']
        if accounts is not None:
            result['accounts'] = [self.get_account_json(account)
                                  for account in accounts]
        if limit is not None:
            result['limit'] = limit
        if publications is None:
            try:
                result['publications_count'] = label['count']
            except KeyError:
                pass
        else:
            result['publications_count'] = len(publications)
            result['publications'] = [self.get_publication_json(publication)
                                      for publication in publications]
        return result


class ApiMixin(object):
    "Mixin for API and JSON handling."

    def get_json_body(self):
        "Return the body of the request interpreted as JSON."
        content_type = self.request.headers.get('Content-Type', '')
        if content_type.startswith(constants.JSON_MIME):
            return json.loads(self.request.body)
        else:
            return {}

    def check_xsrf_cookie(self):
        "Do not check for XSRF cookie when API."
        pass
