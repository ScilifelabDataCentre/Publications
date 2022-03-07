"RequestHandler subclass."

import base64
import json
import logging
import os.path
import urllib.request
import urllib.parse
import urllib.error

import tornado.web

from publications import constants
from publications import settings
from publications import utils


class RequestHandler(tornado.web.RequestHandler):
    "Base request handler."

    def prepare(self):
        "Get the database connection."
        self.db = utils.get_db()

    def get_template_namespace(self):
        "Set the variables accessible within the template."
        result = super(RequestHandler, self).get_template_namespace()
        result["constants"] = constants
        result["settings"] = settings
        result["utils"] = utils
        result["is_admin"] = self.is_admin()
        result["is_curator"] = self.is_curator()
        result["error"] = urllib.parse.unquote_plus(self.get_cookie("error", ""))
        self.clear_cookie("error")
        result["message"] = urllib.parse.unquote_plus(self.get_cookie("message", ""))
        self.clear_cookie("message")
        result["year_counts"] = [
            (r.key, r.value)
            for r in self.db.view(
                "publication", "year", descending=True, reduce=True, group_level=1
            )
        ]
        return result

    def see_other(self, name, *args, **kwargs):
        """Redirect to the absolute URL given by name
        using HTTP status 303 See Other."""
        query = kwargs.copy()
        try:
            self.set_error_flash(query.pop("error"))
        except KeyError:
            pass
        try:
            self.set_message_flash(query.pop("message"))
        except KeyError:
            pass
        url = self.absolute_reverse_url(name, *args, **query)
        self.redirect(url, status=303)

    def absolute_reverse_url(self, name, *args, **query):
        "Get the absolute URL given the handler name, arguments and query."
        if name is None:
            path = ""
        else:
            path = self.reverse_url(name, *args, **query)
        return settings["BASE_URL"].rstrip("/") + path

    def reverse_url(self, name, *args, **query):
        "Allow adding query arguments to the URL."
        url = super(RequestHandler, self).reverse_url(name, *args)
        url = url.rstrip("?")  # tornado bug? sometimes left-over '?'
        # Skip query arguments with None as value
        query = dict([(k, str(v)) for k, v in list(query.items()) if v is not None])
        if query:
            url += "?" + urllib.parse.urlencode(query)
        return url

    def set_message_flash(self, message):
        "Set message flash cookie."
        self.set_flash("message", message)

    def set_error_flash(self, message):
        "Set error flash cookie message."
        self.set_flash("error", message)

    def set_flash(self, name, message):
        message = urllib.parse.quote_plus(message)
        self.set_cookie(name, message)

    def get_doc(self, designname, viewname, key):
        """Get the document with the given id, or from the given view.
        Raise KeyError if not found.
        """
        return utils.get_doc(self.db, designname, viewname, key)

    def get_docs(self, designname, viewname, key=None, last=None, **kwargs):
        """Get the list of documents using the named view
        and the given key or interval.
        """
        return utils.get_docs(
            self.db, designname, viewname, key=key, last=last, **kwargs
        )

    def get_count(self, designname, viewname, key=None):
        "Get the reduce value for the name view and the given key."
        return utils.get_count(self.db, designname, viewname, key=key)

    def get_publication(self, identifier):
        """Get the publication given its IUID, DOI or PMID.
        Raise KeyError if not found.
        """
        return utils.get_publication(self.db, identifier)

    def get_researcher(self, identifier):
        """Get the researcher for the identifier, which is an IUID or an ORCID.
        Raise KeyError if not found.
        """
        return utils.get_researcher(self.db, identifier)

    def get_researchers(self, family, given=None, initials=None):
        """Get the researcher entities for the family name,
        optionally filtering by given name, and/or initials.
        Return a list of researcher documents.
        """
        family = utils.to_ascii(family).lower()
        result = self.get_docs("researcher", "family", key=family)
        if given:
            given = utils.to_ascii(given).lower()
            result = [p for p in result if p["given_normalized"] == given]
        if initials:
            initials = utils.to_ascii(initials).lower()
            result = [
                p for p in result if p["initials_normalized"].startswith(initials)
            ]
        return result

    def get_label(self, identifier):
        """Get the label document by its IUID or value.
        Raise KeyError if not found.
        """
        return utils.get_label(self.db, identifier)

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
        for header in constants.API_KEY_HEADERS:
            try:
                api_key = self.request.headers[header]
            except KeyError:
                pass
            else:
                break
        else:
            raise ValueError
        try:
            account = self.get_doc("account", "api_key", api_key)
        except KeyError:
            raise ValueError
        if account.get("disabled"):
            logging.info(f"API key login: DISABLED {account['email']}")
            return None
        else:
            logging.info(f"API key login: {account['email']}")
            return account

    def get_current_user_session(self):
        """Get the current user from a secure login session cookie.
        Raise ValueError if no or erroneous authentication.
        """
        email = self.get_secure_cookie(
            constants.USER_COOKIE, max_age_days=settings["LOGIN_MAX_AGE_DAYS"]
        )
        if not email:
            raise ValueError
        email = email.decode("utf-8")
        try:
            account = self.get_account(email)
        except KeyError:
            return None
        # Check if login session is invalidated.
        if account.get("login") is None:
            raise ValueError
        if account.get("disabled"):
            logging.info(f"Session authentication: DISABLED {account['email']}")
            return None
        else:
            logging.info(f"Session authentication: {account['email']}")
            return account

    def get_current_user_basic(self):
        """Get the current user by HTTP Basic authentication.
        This should be used only if the site is using TLS (SSL, https).
        Raise ValueError if no or erroneous authentication.
        """
        try:
            auth = self.request.headers["Authorization"]
        except KeyError:
            raise ValueError
        try:
            auth = auth.split()
            if auth[0].lower() != "basic":
                raise ValueError
            auth = base64.b64decode(auth[1])
            email, password = auth.split(":", 1)
            account = self.get_account(email)
            if utils.hashed_password(password) != account.get("password"):
                raise ValueError
        except (IndexError, ValueError, TypeError):
            raise ValueError
        if account.get("disabled"):
            logging.info(f"Basic auth login: DISABLED {account['email']}")
            return None
        else:
            logging.info(f"Basic auth login: {account['email']}")
            return account

    def get_logs(self, iuid):
        "Get the log entries for the document with the given IUID."
        return self.get_docs(
            "log",
            "doc",
            key=[iuid, constants.CEILING],
            last=[iuid, ""],
            descending=True,
        )

    def is_admin(self):
        "Does the current user have the 'admin' role?"
        return bool(self.current_user) and self.current_user["role"] == constants.ADMIN

    def check_admin(self):
        "Check that the current user has the 'admin' role."
        if self.is_admin():
            return
        raise tornado.web.HTTPError(403, reason="Role 'admin' required.")

    def is_curator(self):
        "Does the current user have the 'curator' or 'admin' role?"
        return bool(self.current_user) and self.current_user["role"] in (
            constants.CURATOR,
            constants.ADMIN,
        )

    def check_curator(self):
        "Check that the current user has the 'curator' or 'admin' role."
        if self.is_curator():
            return
        raise tornado.web.HTTPError(403, reason="Role 'curator' required.")

    def is_owner(self, doc):
        """Is the current user the owner of the document?
        Role 'admin' is also allowed."""
        return bool(self.current_user) and (
            self.current_user["email"] == doc["owner"] or self.is_admin()
        )

    def check_owner(self, doc):
        "Check that the current user is the owner of the document."
        if self.is_owner(doc):
            return
        raise tornado.web.HTTPError(403, reason="You are not the owner.")

    def delete_entity(self, doc):
        "Delete the entity and its log entries."
        assert constants.DOCTYPE in doc, "doctype must be defined"
        assert doc[constants.DOCTYPE] in constants.ENTITIES, "must be an entity"
        for log in self.get_logs(doc["_id"]):
            self.db.delete(log)
        self.db.delete(doc)

    def get_publication_json(self, publication, full=True, single=False):
        "JSON representation of publication."
        URL = self.absolute_reverse_url
        result = dict()
        if full:
            result["entity"] = "publication"
            result["iuid"] = publication["_id"]
            if single:
                result["timestamp"] = utils.timestamp()
            result["links"] = dict(
                [
                    ("self", {"href": URL("publication_json", publication["_id"])}),
                    ("display", {"href": URL("publication", publication["_id"])}),
                ]
            )
        result["title"] = publication["title"]
        if full:
            result["authors"] = []
            for author in publication["authors"]:
                au = dict()
                au["family"] = author.get("family")
                au["given"] = author.get("given")
                au["initials"] = author.get("initials")
                if author.get("researcher"):
                    researcher = self.get_researcher(author["researcher"])
                    if researcher.get("orcid"):
                        au["orcid"] = researcher["orcid"]
                    au["researcher"] = {
                        "href": URL("researcher_json", author["researcher"])
                    }
                result["authors"].append(au)
            result["type"] = publication.get("type")
        result["published"] = publication.get("published")
        result["journal"] = publication.get("journal")
        # XXX Kludge: this is not stored in the publication, since it is
        # not obtained (or at least not parsed) from PubMed or Crossref.
        result["journal"]["issn-l"] = self.get_issn_l(result["journal"].get("issn"))
        if full:
            result["abstract"] = publication.get("abstract")
        result["doi"] = publication.get("doi")
        result["pmid"] = publication.get("pmid")
        result["labels"] = publication.get("labels") or []
        result["xrefs"] = publication.get("xrefs") or []
        if full:
            result["notes"] = publication.get("notes") or []
            result["created"] = publication["created"]
            result["modified"] = publication["modified"]
        return result

    def get_account_json(self, account, full=False):
        "JSON representation of account."
        URL = self.absolute_reverse_url
        result = dict()
        result["entity"] = "account"
        result["iuid"] = account["_id"]
        result["timestamp"] = utils.timestamp()
        result["links"] = dict(
            [
                ("self", {"href": URL("account_json", account["email"])}),
                ("display", {"href": URL("account", account["email"])}),
            ]
        )
        result["email"] = account["email"]
        result["name"] = account.get("name")  # May be absent.
        result["role"] = account["role"]
        result["status"] = account.get("disabled") and "disabled" or "enabled"
        result["login"] = account.get("login")
        if full:
            result["api_key"] = account.get("api_key")
            result["labels"] = labels = []
            for label in account["labels"]:
                links = dict()
                links["self"] = {"href": URL("label_json", label)}
                links["display"] = {"href": URL("label", label)}
                labels.append(dict([("value", label), ("links", links)]))
        result["created"] = account["created"]
        result["modified"] = account["modified"]
        return result

    def get_label_json(self, label, publications=None, accounts=None):
        "JSON representation of label."
        URL = self.absolute_reverse_url
        result = dict()
        result["entity"] = "label"
        result["iuid"] = label["_id"]
        result["timestamp"] = utils.timestamp()
        result["links"] = links = dict()
        links["self"] = {"href": URL("label_json", label["value"])}
        links["display"] = {"href": URL("label", label["value"])}
        result["value"] = label["value"]
        if settings["TEMPORAL_LABELS"]:
            result["started"] = label.get("started")
            result["ended"] = label.get("ended")
        result["created"] = label["created"]
        result["modified"] = label["modified"]
        if accounts is not None:
            result["accounts"] = [
                self.get_account_json(account) for account in accounts
            ]
        if publications is None:
            try:
                result["publications_count"] = label["count"]
            except KeyError:
                pass
        else:
            result["publications_count"] = len(publications)
            result["publications"] = [
                self.get_publication_json(publication) for publication in publications
            ]
        return result

    def get_issn_l(self, issn):
        """Get the ISSN-L for the ISSN. Returns None if none found.
        Lazy evaluation; fetch the mapping only when actually requested.
        """
        try:
            return self._issn_l_map.get(issn)
        except AttributeError:
            self._issn_l_map = dict(
                [(r.value, r.key) for r in self.db.view("journal", "issn_l")]
            )
            return self._issn_l_map.get(issn)


class ApiMixin:
    "Mixin for API and JSON handling."

    def get_json_body(self):
        "Return the body of the request interpreted as JSON."
        content_type = self.request.headers.get("Content-Type", "")
        if content_type.startswith(constants.JSON_MIME):
            return json.loads(self.request.body)
        else:
            return {}

    def check_xsrf_cookie(self):
        "Do not check for XSRF cookie when API."
        pass
