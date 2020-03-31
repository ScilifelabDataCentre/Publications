"Label pages."

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
    "Label page, containing list of publications partitioned by year."

    def get(self, identifier):
        try:
            label = self.get_label(identifier)
        except KeyError as error:
            self.see_other('home', error=str(error))
            return
        accounts = self.get_docs('account/label',
                                 key=label['value'].lower())
        publications = self.get_docs('publication/label',
                                     key=label['value'].lower())
        publications.sort(key=lambda i: i['published'], reverse=True)
        # This is inefficient; really shouldn't fetch those 
        # beyond the limit in the first place, but we want
        # the latest publications, and the index is such that
        # we have to get all to do the sorting here.
        limit = self.get_limit()
        if limit:
            publications = publications[:limit]
        self.render('label.html',
                    label=label,
                    accounts=accounts,
                    publications=publications,
                    limit=limit)

    @tornado.web.authenticated
    def post(self, identifier):
        if self.get_argument('_http_method', None) == 'delete':
            self.delete(identifier)
            return
        raise tornado.web.HTTPError(
            405, reason='Internal problem; POST only allowed for DELETE.')

    @tornado.web.authenticated
    def delete(self, identifier):
        self.check_admin()
        try:
            label = self.get_label(identifier)
        except KeyError as error:
            self.see_other('labels', error=str(error))
            return
        value = label['value']
        # Do it in this order; safer if interrupted.
        for publication in self.get_docs('publication/label',
                                         key=value.lower()):
            with PublicationSaver(publication, rqh=self) as saver:
                labels = publication['labels'].copy()
                labels.pop(value, None)
                labels.pop(value.lower(), None)
                saver['labels'] = labels
        for account in self.get_docs('account/label', key=value.lower()):
            with AccountSaver(account, rqh=self) as saver:
                labels = set(account['labels'])
                labels.discard(value)
                saver['labels'] = sorted(labels)
        self.delete_entity(label)
        self.see_other('labels')


class LabelJson(Label):
    "Label JSON data."

    def render(self, template, **kwargs):
        params = dict(publications=kwargs['publications'],
                      accounts=kwargs['accounts'])
        if kwargs.get('limit'):
            params['limit'] = kwargs['limit']
        self.write(self.get_label_json(kwargs['label'], **params))


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
            label['count'] = counts.get(label['value'].lower(), 0)
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
            self.see_other('label_add', error='no label provided')
            return
        try:
            with LabelSaver(rqh=self) as saver:
                saver.set_value(value)
            label = saver.doc
        except ValueError as error:
            self.set_error_flash(str(error))
            self.see_other('label_add')
            return
        self.see_other('label', label['value'])


class LabelEdit(RequestHandler):
    "Label edit page."

    @tornado.web.authenticated
    def get(self, identifier):
        self.check_admin()
        try:
            label = self.get_label(identifier)
        except KeyError as error:
            self.see_other('labels', error=str(error))
            return
        self.render('label_edit.html', label=label)

    @tornado.web.authenticated
    def post(self, identifier):
        self.check_admin()
        try:
            label = self.get_label(identifier)
        except KeyError as error:
            self.see_other('labels', error=str(error))
            return
        old_value = label['value']
        new_value = self.get_argument('value')
        try:
            with LabelSaver(label, rqh=self) as saver:
                saver.check_revision()
                saver.set_value(new_value)
                saver['href'] = self.get_argument('href', None)
                saver['description'] = self.get_argument('description', None)
        except SaverError:
            self.set_error_flash(utils.REV_ERROR)
            self.see_other('label', label['value'])
            return
        if new_value != old_value:
            for account in self.get_docs('account/label',
                                         key=old_value.lower()):
                with AccountSaver(account, rqh=self) as saver:
                    labels = set(account['labels'])
                    labels.discard(old_value)
                    labels.discard(old_value.lower())
                    labels.add(new_value)
                    saver['labels'] = sorted(labels)
            for publication in self.get_docs('publication/label',
                                             key=old_value.lower()):
                if old_value in publication['labels']:
                    with PublicationSaver(publication, rqh=self) as saver:
                        labels = publication['labels'].copy()
                        labels[new_value] = labels.pop(old_value)
                        saver['labels'] = labels
        self.see_other('label', label['value'])


class LabelMerge(RequestHandler):
    "Merge label into another."

    @tornado.web.authenticated
    def get(self, identifier):
        self.check_admin()
        try:
            label = self.get_label(identifier)
        except KeyError as error:
            self.see_other('labels', error=str(error))
            return
        self.render('label_merge.html',
                    label=label,
                    labels=self.get_docs('label/value'))

    @tornado.web.authenticated
    def post(self, identifier):
        self.check_admin()
        try:
            label = self.get_label(identifier)
        except KeyError as error:
            self.see_other('labels', error=str(error))
            return
        try:
            merge = self.get_label(self.get_argument('merge'))
        except tornado.web.MissingArgumentError:
            self.set_error_flash('no merge label provided')
            self.see_other('labels')
            return
        except KeyError as error:
            self.set_error_flash(str(error))
            self.see_other('labels')
            return
        old_label = label['value']
        new_label = merge['value']
        self.delete_entity(label)
        for account in self.get_docs('account/label', key=old_label.lower()):
            with AccountSaver(account, rqh=self) as saver:
                labels = set(account['labels'])
                labels.discard(old_label)
                labels.discard(old_label.lower())
                labels.add(new_label)
                saver['labels'] = sorted(labels)
        for publication in self.get_docs('publication/label',
                                         key=old_label.lower()):
            with PublicationSaver(publication, rqh=self) as saver:
                labels = publication['labels'].copy()
                qual = labels.pop(old_label, None) or \
                       labels.pop(old_label.lower(), None)
                labels[new_label] = labels.get(new_label) or qual
                saver['labels'] = labels
        self.see_other('label', new_label)
