"Label pages."

from __future__ import print_function

import logging

import tornado.web

from . import constants
from . import settings
from . import utils
from .requesthandler import RequestHandler
from .saver import Saver, SaverError
from .account import AccountSaver
from .publication import PublicationSaver


class LabelSaver(Saver):
    doctype = constants.LABEL

    def check_value(self, value):
        "Value must be unique."
        try:
            label = self.rqh.get_label(value)
            if label['_id'] == self.doc.get('_id'): return
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
        accounts = self.get_docs('account/label', key=label['value'])
        publications = self.get_docs('publication/label',
                                     key=label['value'],
                                     reduce=False)
        publications.sort(key=lambda i: i['published'], reverse=True)
        self.render('label.html',
                    label=label,
                    accounts=accounts,
                    publications=publications)


class LabelsList(RequestHandler):
    "Labels list page."

    def get(self):
        labels = self.get_docs('label/value')
        view = self.db.view('publication/label', group=True)
        label_counts = dict([(r.key, r.value) for r in view])
        self.render('labels_list.html',
                    labels=labels,
                    label_counts=label_counts)


class LabelsTable(RequestHandler):
    "Labels table page."

    def get(self):
        labels = self.get_docs('label/value')
        label_accounts = dict([(l['value'], []) for l in labels])
        for account in self.get_docs('account/email'):
            for label in account['labels']:
                label_accounts[label].append(account['email'])
        view = self.db.view('publication/label', group=True)
        label_counts = dict([(r.key, r.value) for r in view])
        self.render('labels_table.html',
                    labels=labels,
                    label_accounts=label_accounts,
                    label_counts=label_counts)


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

    @tornado.web.authenticated
    def get(self, identifier):
        self.check_admin()
        try:
            label = self.get_label(identifier)
        except KeyError, msg:
            self.see_other('labels', error=str(msg))
            return
        self.render('label_edit.html', label=label)

    @tornado.web.authenticated
    def post(self, identifier):
        self.check_admin()
        try:
            label = self.get_label(identifier)
        except KeyError, msg:
            self.see_other('labels', error=str(msg))
            return
        old_value = label['value']
        new_value = self.get_argument('value')
        try:
            with LabelSaver(label, rqh=self) as saver:
                saver.check_revision()
                saver['value'] = new_value
                saver['value_normalized'] = utils.to_ascii(new_value)
        except SaverError:
            self.see_other('label', label['value'], error=utils.REV_ERROR)
            return
        for account in self.get_docs('account/label', key=old_value):
            with AccountSaver(account, rqh=self) as saver:
                labels = set(account['labels'])
                labels.discard(old_value)
                labels.add(new_value)
                saver['labels'] = sorted(labels)
        for publication in self.get_docs('publication/label',
                                         key=old_value,
                                         reduce=False):
            with PublicationSaver(publication, rqh=self) as saver:
                labels = set(publication['labels'])
                labels.discard(old_value)
                labels.add(new_value)
                saver['labels'] = sorted(labels)
        self.see_other('label', label['value'])


class LabelDelete(RequestHandler):
    "Label delete."

    @tornado.web.authenticated
    def post(self, identifier):
        self.check_admin()
        try:
            label = self.get_label(identifier)
        except KeyError, msg:
            self.see_other('labels', error=str(msg))
            return
        value = label['value']
        self.db.delete(label)
        for account in self.get_docs('account/label', key=value):
            with AccountSaver(account, rqh=self) as saver:
                labels = set(account['labels'])
                labels.discard(value)
                saver['labels'] = sorted(labels)
        for publication in self.get_docs('publication/label',
                                         key=value,
                                         reduce=False):
            with PublicationSaver(publication, rqh=self) as saver:
                labels = set(publication['labels'])
                labels.discard(value)
                saver['labels'] = sorted(labels)
        self.see_other('labels_list')
