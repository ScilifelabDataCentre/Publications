"Publications: Context handler for saving an entity as a CouchDB document. "

from __future__ import print_function

import logging

import couchdb
import tornado.web

from publications import constants
from publications import utils


class Saver(object):
    "Context manager saving the data for the document."

    doctype = None

    def __init__(self, doc=None, rqh=None, db=None):
        assert self.doctype
        if rqh is not None:
            self.rqh = rqh
            self.db = rqh.db
        elif db is not None:
            self.rqh = None
            self.db = db
        else:
            raise AttributeError('neither db nor rqh given')
        self.doc = doc or dict()
        self.changed = dict()
        if '_id' in self.doc:
            assert self.doctype == self.doc[constants.DOCTYPE]
        else:
            self.doc[constants.DOCTYPE] = self.doctype
            self.doc['_id'] = utils.get_iuid()
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
            raise IOError('document revision update conflict')
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
            self.changed[key] == '__del__'

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def initialize(self):
        "Set the initial values for the new document."
        try:
            self.doc['owner'] = self.rqh.current_user['email']
        except (TypeError, AttributeError, KeyError):
            self.doc['owner'] = None
        self.doc['created'] = utils.timestamp()

    def setup(self):
        "Any additional setup. To be redefined."
        pass

    def finalize(self):
        "Perform any final modifications before saving the document."
        self.doc['modified'] = utils.timestamp()

    def post_process(self):
        "Perform any actions after having saved the document."
        pass

    def write_log(self):
        "Create a log entry for the change."
        utils.write_log(self.db, self.rqh, self.doc, changed=self.changed)
