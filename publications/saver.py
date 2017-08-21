"Context handler for saving a document. "

from __future__ import print_function

import logging

import couchdb
import tornado.web

from publications import constants
from publications import utils


class SaverError(Exception):
    "Revision mismatch error."
    pass


class Saver(object):
    "Context manager saving the data for the document."

    doctype = None

    def __init__(self, doc=None, rqh=None, db=None, account=None):
        assert self.doctype in constants.ENTITIES
        if rqh is not None:
            self.rqh = rqh
            self.db = rqh.db
            self.account = account or rqh.current_user
        elif db is not None:
            self.rqh = None
            self.db = db
            self.account = account
        else:
            raise AttributeError('neither db nor rqh given')
        self.doc = doc or dict()
        self.changed = dict()
        if '_id' in self.doc:
            assert self.doctype == self.doc[constants.DOCTYPE]
        else:
            self.doc['_id'] = utils.get_iuid()
            self.doc[constants.DOCTYPE] = self.doctype
            self.initialize()
        self.setup()

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        if type is not None: return False # No exceptions handled here.
        self.finalize()
        try:
            self.db.save(self.doc)
        except couchdb.http.ResourceConflict:
            raise SaverError
        self.post_process()
        self.write_log()

    def __setitem__(self, key, value):
        "Update the key/value pair."
        try:
            checker = getattr(self, "check_{0}".format(key))
        except AttributeError:
            pass
        else:
            checker(value)
        try:
            converter = getattr(self, "convert_{0}".format(key))
        except AttributeError:
            pass
        else:
            value = converter(value)
        try:
            if self.doc[key] == value: return
        except KeyError:
            pass
        self.doc[key] = value
        self.changed[key] = value

    def __getitem__(self, key):
        return self.doc[key]

    def __delitem__(self, key):
        try:
            del self.doc[key]
        except AttributeError:
            pass
        else:
            self.changed[key] = '__del__'

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def initialize(self):
        "Set the initial values for the new document."
        try:
            self.doc['account'] = self.rqh.current_user['email']
        except (TypeError, AttributeError, KeyError):
            self.doc['account'] = None
        self.doc['created'] = utils.timestamp()

    def setup(self):
        "Any additional setup. To be redefined."
        pass

    def check_revision(self):
        """If the document is not new, check that the form field
        argument '_rev', if it exists, matches the document.
        Raise Saverrror if incorrect.
        """
        old_rev = self.doc.get('_rev')
        if not old_rev: return
        if self.rqh is None: return
        new_rev = self.rqh.get_argument('_rev', None)
        if not new_rev: return
        if old_rev != new_rev:
            raise SaverError

    def finalize(self):
        "Perform any final modifications before saving the document."
        self.doc['modified'] = utils.timestamp()

    def post_process(self):
        "Perform any actions after having saved the document."
        pass

    def write_log(self):
        "Write a log entry for the change."
        # utils.write_log(self.db, self.rqh, self.doc, changed=self.changed)
        log = dict(_id=utils.get_iuid(),
                   doc=self.doc['_id'],
                   doctype=self.doc[constants.DOCTYPE],
                   changed=self.changed,
                   modified=utils.timestamp())
        log[constants.DOCTYPE] = constants.LOG
        if self.rqh:
            # xheaders argument to HTTPServer takes care of X-Real-Ip
            # and X-Forwarded-For
            log['remote_ip'] = self.rqh.request.remote_ip
            try:
                log['user_agent'] = self.rqh.request.headers['User-Agent']
            except KeyError:
                pass
        if self.account:
            try:
                log['account'] = self.account['email']
            except KeyError:
                pass
        self.db.save(log)
