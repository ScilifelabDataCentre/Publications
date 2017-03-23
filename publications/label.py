"Label pages."

from __future__ import print_function

import logging

import tornado.web

from . import constants
from . import settings
from . import utils
from .requesthandler import RequestHandler
from .saver import Saver


class LabelSaver(Saver):
    doctype = constants.LABEL

    def check_value(self, value):
        "Value must be unique."
        try:
            label = self.rqh.get_label(value)
        except KeyError:
            pass
        else:
            raise ValueError("label '%s' is not unique" % value)


class Label(RequestHandler):
    "Label page."

    def get(self, value):
        try:
            label = self.get_label(value)
        except KeyError, msg:
            self.see_other('home', error=str(msg))
            return
        self.render('label.html', label=label)


class Labels(RequestHandler):
    "Labels list page."

    @tornado.web.authenticated
    def get(self):
        self.check_admin()
        labels = self.get_docs('label/value', key=None)
        self.render('labels.html', labels=labels)


class LabelAdd(RequestHandler):
    "Label addition page."

    @tornado.web.authenticated
    def get(self):
        self.check_admin()
        self.render('label_add.html')

    @tornado.web.authenticated
    def post(self):
        self.check_admin()
        try:
            value = self.get_argument('value')
        except tornado.web.MissingArgumentError:
            self.see_other('label_add', error='No label provided.')
            return
        try:
            with LabelSaver(rqh=self) as saver:
                saver['value'] = value
                saver['value_normalized'] = utils.to_ascii(value)
            label = saver.doc
        except ValueError, msg:
            self.see_other('label_add', error=str(msg))
            return
        self.see_other('label', label['value'])


class LabelEdit(RequestHandler):
    "Label edit page."


class LabelDelete(RequestHandler):
    "Label Delete page."
