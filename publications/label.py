"Label pages."

from __future__ import print_function

import logging
from collections import OrderedDict as OD

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

    def set_value(self, value):
        self['value'] = value
        self['normalized_value'] = utils.to_ascii(value).lower()

    def check_value(self, value):
        "Value must be unique."
        try:
            label = utils.get_label(self.db, value)
            if label['_id'] == self.doc.get('_id'): return
        except KeyError:
            pass
        else:
            raise ValueError("label '%s' is not unique" % value)


class Label(RequestHandler):
    "Label page."

    def get(self, identifier):
        try:
            label = self.get_label(identifier)
        except KeyError, msg:
            self.see_other('home', error=str(msg))
            return
        accounts = self.get_docs('account/label', key=label['value'])
        publications = self.get_docs('publication/label', key=label['value'])
        publications.sort(key=lambda i: i['published'], reverse=True)
        self.render('label.html',
                    label=label,
                    accounts=accounts,
                    publications=publications)

    @tornado.web.authenticated
    def post(self, identifier):
        if self.get_argument('_http_method', None) == 'delete':
            self.delete(identifier)
            return
        raise tornado.web.HTTPError(
            405, reason='Internal problem; POST only allowed for DELETE.')

    @tornado.web.authenticated
    def post(self, identifier):
        self.check_admin()
        try:
            label = self.get_label(identifier)
        except KeyError, msg:
            self.see_other('labels', error=str(msg))
            return
        value = label['value']
        self.delete_entity(label)
        for account in self.get_docs('account/label', key=value):
            with AccountSaver(account, rqh=self) as saver:
                labels = set(account['labels'])
                labels.discard(value)
                saver['labels'] = sorted(labels)
        for publication in self.get_docs('publication/label', key=value):
            with PublicationSaver(publication, rqh=self) as saver:
                labels = set(publication['labels'])
                labels.discard(value)
                saver['labels'] = sorted(labels)
        self.see_other('labels')


class LabelJson(Label):
    "Label JSON data."

    def render(self, template, **kwargs):
        self.write(self.get_label_json(kwargs['label'],
                                       full=True,
                                       publications=kwargs['publications'],
                                       accounts=kwargs['accounts']))


class LabelsList(RequestHandler):
    "Labels list page."

    def get(self):
        labels = self.get_docs('label/value')
        self.render('labels.html', labels=labels)


class LabelsTable(RequestHandler):
    "Labels table page."

    def get(self):
        labels = self.get_docs('label/value')
        if self.is_curator():
            accounts = dict([(l['value'], []) for l in labels])
            for account in self.get_docs('account/email'):
                for label in account['labels']:
                    accounts.setdefault(label, []).append(account['email'])
            for label in labels:
                label['accounts'] = sorted(accounts.get(label['value'], []))
        view = self.db.view('publication/label', group=True)
        counts = dict([(r.key, r.value) for r in view])
        for label in labels:
            label['count'] = counts.get(label['value'], 0)
        self.render('labels_table.html', labels=labels)


class LabelsJson(LabelsTable):
    "JSON for labels."

    def render(self, template, **kwargs):
        URL = self.absolute_reverse_url
        labels = kwargs['labels']
        result = OD()
        result['entity'] = 'labels'
        result['timestamp'] = utils.timestamp()
        result['links'] = links = OD()
        links['self'] = {'href': URL('labels_json')}
        links['display'] = {'href': URL('labels')}
        result['labels_count'] = len(labels)
        result['labels'] = [self.get_label_json(l) for l in labels]
        self.write(result)


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
                saver.set_value(value)
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
                saver.set_value(new_value)
        except SaverError:
            self.see_other('label', label['value'], error=utils.REV_ERROR)
            return
        for account in self.get_docs('account/label', key=old_value):
            with AccountSaver(account, rqh=self) as saver:
                labels = set(account['labels'])
                labels.discard(old_value)
                labels.add(new_value)
                saver['labels'] = sorted(labels)
        for publication in self.get_docs('publication/label', key=old_value):
            with PublicationSaver(publication, rqh=self) as saver:
                labels = set(publication['labels'])
                labels.discard(old_value)
                labels.add(new_value)
                saver['labels'] = sorted(labels)
        self.see_other('label', label['value'])
