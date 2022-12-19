"Label pages."

import logging

import tornado.web

from publications import constants
from publications import settings
from publications import utils
from publications.requesthandler import CorsMixin, RequestHandler
from publications.saver import Saver, SaverError
from publications.account import AccountSaver
from publications.publication import PublicationSaver
from publications.subset import Subset


DESIGN_DOC = {
    "views": {
        "normalized_value": {
            "map": """function (doc) {
  if (doc.publications_doctype !== 'label') return;
  emit(doc.normalized_value, doc.value);
}"""
        },
        "value": {
            "reduce": "_count",
            "map": """function (doc) {
  if (doc.publications_doctype !== 'label') return;
  emit(doc.value, null);
}""",
        },
        "current": {
            "map": """function (doc) {
  if (doc.publications_doctype !== 'label') return;
  if (doc.ended) return;
  if (doc.secondary) return;
  emit(doc.started, doc.value);
}"""
        },
    }
}


def load_design_document(db):
    "Update the CouchDB design document."
    if db.put_design("label", DESIGN_DOC):
        logging.info("Updated 'label' design document.")


class LabelSaver(Saver):
    doctype = constants.LABEL

    def set_value(self, value):
        self["value"] = value
        self["normalized_value"] = utils.to_ascii(value).lower()

    def set_secondary(self, value):
        self["secondary"] = utils.to_bool(value)

    def check_value(self, value):
        "Value must be unique."
        try:
            label = utils.get_label(self.db, value)
            if label["_id"] == self.doc.get("_id"):
                return
        except KeyError:
            pass
        else:
            raise ValueError(f"label '{value}' already exists")
        if value.endswith("/edit"):
            raise ValueError("label may not end with '/edit'")
        if value.endswith("/merge"):
            raise ValueError("label may not end with '/merge'")


class Label(RequestHandler):
    "Label page, containing list of publications partitioned by year."

    def get(self, identifier):
        try:
            label = self.get_label(identifier)
        except KeyError as error:
            self.see_other("home", error=str(error))
            return
        accounts = self.get_docs("account", "label", key=label["value"].lower())
        publications = list(Subset(self.db, label=label["value"]))
        self.render(
            "label.html", label=label, accounts=accounts, publications=publications
        )

    @tornado.web.authenticated
    def post(self, identifier):
        if self.get_argument("_http_method", None) == "delete":
            self.delete(identifier)
            return
        raise tornado.web.HTTPError(
            405, reason="Internal problem; POST only allowed for DELETE."
        )

    @tornado.web.authenticated
    def delete(self, identifier):
        self.check_admin()
        try:
            label = self.get_label(identifier)
        except KeyError as error:
            self.see_other("labels", error=str(error))
            return
        value = label["value"]
        # Do it in this order; safer if interrupted.
        publications = list(Subset(self.db, label=label["value"]))
        for publication in publications:
            with PublicationSaver(publication, rqh=self) as saver:
                labels = publication["labels"].copy()
                labels.pop(value, None)
                labels.pop(value.lower(), None)
                saver["labels"] = labels
        for account in self.get_docs("account", "label", key=value.lower()):
            with AccountSaver(account, rqh=self) as saver:
                labels = set(account["labels"])
                labels.discard(value)
                saver["labels"] = sorted(labels)
        self.delete_entity(label)
        self.see_other("labels")


class LabelJson(CorsMixin, Label):
    "Label JSON output."

    def render(self, template, **kwargs):
        self.write(
            self.get_label_json(
                kwargs["label"],
                publications=kwargs["publications"],
                accounts=kwargs["accounts"],
            )
        )


class LabelsList(RequestHandler):
    """Labels list page. By default only current labels,
    if the TEMPORAL_LABELS setting is not None.
    """

    def get(self):
        if settings["TEMPORAL_LABELS"]:
            all = utils.to_bool(self.get_argument("all", False))
            if all:
                labels = self.get_docs("label", "value")
            else:
                labels = self.get_docs("label", "current")
        else:
            labels = self.get_docs("label", "value")
            all = None
        labels.sort(key=lambda d: d["value"].lower())
        self.render("labels.html", labels=labels, all=all)


class LabelsTable(RequestHandler):
    "Labels table page."

    def get(self):
        labels = self.get_docs("label", "value")
        labels.sort(key=lambda d: d["value"].lower())
        if self.is_curator():
            accounts = dict([(l["value"], []) for l in labels])
            for account in self.get_docs("account", "email"):
                for label in account["labels"]:
                    accounts.setdefault(label, []).append(account["email"])
            for label in labels:
                label["accounts"] = sorted(accounts.get(label["value"], []))
        view = self.db.view("publication", "label", group=True)
        counts = dict([(r.key, r.value) for r in view])
        for label in labels:
            label["count"] = counts.get(label["value"].lower(), 0)
        self.render("labels_table.html", labels=labels)


class LabelsJson(CorsMixin, LabelsTable):
    "Labels JSON output."

    def render(self, template, **kwargs):
        URL = self.absolute_reverse_url
        labels = kwargs["labels"]
        result = dict()
        result["entity"] = "labels"
        result["timestamp"] = utils.timestamp()
        result["links"] = links = dict()
        links["self"] = {"href": URL("labels_json")}
        links["display"] = {"href": URL("labels")}
        result["labels_count"] = len(labels)
        result["labels"] = [self.get_label_json(l) for l in labels]
        self.write(result)


class LabelAdd(RequestHandler):
    "Label addition page."

    @tornado.web.authenticated
    def get(self):
        self.check_admin()
        self.render("label_add.html")

    @tornado.web.authenticated
    def post(self):
        self.check_admin()
        try:
            value = self.get_argument("value")
        except tornado.web.MissingArgumentError:
            self.see_other("label_add", error="no label provided")
            return
        try:
            with LabelSaver(rqh=self) as saver:
                saver.set_value(value)
                saver.set_secondary(self.get_argument("secondary", None))
            label = saver.doc
        except ValueError as error:
            self.set_error_flash(str(error))
            self.see_other("label_add")
            return
        self.see_other("label", label["value"])


class LabelEdit(RequestHandler):
    "Label edit page."

    @tornado.web.authenticated
    def get(self, identifier):
        self.check_admin()
        try:
            label = self.get_label(identifier)
        except KeyError as error:
            self.see_other("labels", error=str(error))
            return
        self.render("label_edit.html", label=label)

    @tornado.web.authenticated
    def post(self, identifier):
        self.check_admin()
        try:
            label = self.get_label(identifier)
        except KeyError as error:
            self.see_other("labels", error=str(error))
            return
        old_value = label["value"]
        new_value = self.get_argument("value")
        try:
            with LabelSaver(label, rqh=self) as saver:
                saver.check_revision()
                saver.set_value(new_value)
                saver.set_secondary(self.get_argument("secondary", None))
                saver["href"] = self.get_argument("href", None)
                saver["description"] = self.get_argument("description", None)
                if settings["TEMPORAL_LABELS"]:
                    saver["started"] = self.get_argument("started", "") or None
                    saver["ended"] = self.get_argument("ended", "") or None
        except SaverError:
            self.set_error_flash(constants.REV_ERROR)
            self.see_other("label", label["value"])
            return
        except ValueError as error:
            self.set_error_flash(str(error))
            self.see_other("label_edit", old_value)
            return
        if new_value != old_value:
            for account in self.get_docs("account", "label", key=old_value.lower()):
                with AccountSaver(account, rqh=self) as saver:
                    labels = set(account["labels"])
                    labels.discard(old_value)
                    labels.discard(old_value.lower())
                    labels.add(new_value)
                    saver["labels"] = sorted(labels)
            for publication in Subset(self.db, label=old_value):
                if old_value in publication["labels"]:
                    with PublicationSaver(publication, rqh=self) as saver:
                        labels = publication["labels"].copy()
                        labels[new_value] = labels.pop(old_value)
                        saver["labels"] = labels
        self.see_other("label", label["value"])


class LabelMerge(RequestHandler):
    "Merge label into another."

    @tornado.web.authenticated
    def get(self, identifier):
        self.check_admin()
        try:
            label = self.get_label(identifier)
        except KeyError as error:
            self.see_other("labels", error=str(error))
            return
        self.render(
            "label_merge.html", label=label, labels=self.get_docs("label", "value")
        )

    @tornado.web.authenticated
    def post(self, identifier):
        self.check_admin()
        try:
            label = self.get_label(identifier)
        except KeyError as error:
            self.see_other("labels", error=str(error))
            return
        try:
            merge = self.get_label(self.get_argument("merge"))
        except tornado.web.MissingArgumentError:
            self.set_error_flash("no merge label provided")
            self.see_other("labels")
            return
        except KeyError as error:
            self.set_error_flash(str(error))
            self.see_other("labels")
            return
        old_label = label["value"]
        new_label = merge["value"]
        self.delete_entity(label)
        for account in self.get_docs("account", "label", key=old_label.lower()):
            with AccountSaver(account, rqh=self) as saver:
                labels = set(account["labels"])
                labels.discard(old_label)
                labels.discard(old_label.lower())
                labels.add(new_label)
                saver["labels"] = sorted(labels)
        for publication in Subset(self.db, label=old_label):
            with PublicationSaver(publication, rqh=self) as saver:
                labels = publication["labels"].copy()
                qual = labels.pop(old_label, None) or labels.pop(
                    old_label.lower(), None
                )
                labels[new_label] = labels.get(new_label) or qual
                saver["labels"] = labels
        self.see_other("label", new_label)
