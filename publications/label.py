"Label pages."

import csv
import io

import tornado.web
import tornado.escape

from publications import constants
from publications import settings
from publications import utils
from publications.requesthandler import CorsMixin, RequestHandler

import publications.account
import publications.publication
import publications.saver
import publications.subset


class LabelSaver(publications.saver.Saver):
    doctype = constants.LABEL

    def set_value(self, value):
        self["value"] = value
        self["normalized_value"] = utils.to_ascii(value).lower()

    def set_secondary(self, value):
        self["secondary"] = utils.to_bool(value)

    def check_value(self, value):
        "Value must be unique."
        try:
            label = publications.database.get_label(self.db, value)
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
        self.render(
            "label/display.html",
            label=label,
            accounts=self.get_docs("account", "label", key=label["value"].lower()),
            publications=list(
                publications.subset.Subset(self.db, label=label["value"])
            ),
            escaped_label=tornado.escape.url_escape(label['value']),
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
        for publication in publications.subset.Subset(self.db, label=label["value"]):
            with publications.publication.PublicationSaver(
                publication, rqh=self
            ) as saver:
                labels = publication["labels"].copy()
                labels.pop(value, None)
                labels.pop(value.lower(), None)
                saver["labels"] = labels
        for account in self.get_docs("account", "label", key=value.lower()):
            with publications.account.AccountSaver(account, rqh=self) as saver:
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
        self.render("labels/list.html", labels=labels, all=all)


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
        self.render("labels/table.html", labels=labels)


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


class LabelCreate(RequestHandler):
    "Label creation page."

    @tornado.web.authenticated
    def get(self):
        self.check_admin()
        self.render("label/create.html")

    @tornado.web.authenticated
    def post(self):
        self.check_admin()
        try:
            value = self.get_argument("value")
        except tornado.web.MissingArgumentError:
            self.see_other("label_create", error="no label provided")
            return
        try:
            with LabelSaver(rqh=self) as saver:
                saver.set_value(value)
                saver.set_secondary(self.get_argument("secondary", None))
            label = saver.doc
        except ValueError as error:
            self.set_error_flash(str(error))
            self.see_other("label_create")
            return
        self.see_other("label", label["value"])


class LabelEdit(RequestHandler):
    "Label edit page."

    @tornado.web.authenticated
    def get(self, identifier):
        self.check_admin()
        try:
            label = self.get_label(tornado.escape.url_unescape(identifier))
        except KeyError as error:
            self.see_other("labels", error=str(error))
            return
        self.render("label/edit.html", label=label, escaped_label=identifier)

    @tornado.web.authenticated
    def post(self, identifier):
        self.check_admin()
        try:
            label = self.get_label(tornado.escape.url_unescape(identifier))
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
        except publications.saver.SaverError:
            self.set_error_flash(constants.REV_ERROR)
            self.see_other("label", label["value"])
            return
        except ValueError as error:
            self.set_error_flash(str(error))
            self.see_other("label_edit", old_value)
            return
        if new_value != old_value:
            for account in self.get_docs("account", "label", key=old_value.lower()):
                with publications.account.AccountSaver(account, rqh=self) as saver:
                    labels = set(account["labels"])
                    labels.discard(old_value)
                    labels.discard(old_value.lower())
                    labels.add(new_value)
                    saver["labels"] = sorted(labels)
            for publication in publications.subset.Subset(self.db, label=old_value):
                if old_value in publication["labels"]:
                    with publications.publication.PublicationSaver(
                        publication, rqh=self
                    ) as saver:
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
            "label/merge.html", label=label, labels=self.get_docs("label", "value")
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
            with publications.account.AccountSaver(account, rqh=self) as saver:
                labels = set(account["labels"])
                labels.discard(old_label)
                labels.discard(old_label.lower())
                labels.add(new_label)
                saver["labels"] = sorted(labels)
        for publication in publications.subset.Subset(self.db, label=old_label):
            with publications.publication.PublicationSaver(
                publication, rqh=self
            ) as saver:
                labels = publication["labels"].copy()
                qual = labels.pop(old_label, None) or labels.pop(
                    old_label.lower(), None
                )
                labels[new_label] = labels.get(new_label) or qual
                saver["labels"] = labels
        self.see_other("label", new_label)


class LabelAdd(RequestHandler):
    "Add a label to a set of publications."

    @tornado.web.authenticated
    def get(self, identifier):
        self.check_admin()
        print(identifier)
        try:
            label = self.get_label(identifier)
        except KeyError as error:
            self.see_other("labels", error=str(error))
            return
        self.render("label/add.html", label=label["value"])

    @tornado.web.authenticated
    def post(self, identifier):
        self.check_admin()
        try:
            label = self.get_label(identifier)
        except KeyError as error:
            self.see_other("labels", error=str(error))
            return
        try:
            infile = self.request.files["publications"][0]
        except tornado.web.MissingArgumentError:
            self.set_error_flash("no publications subset file provided")
            self.see_other("label", label)
            return
        with io.StringIO(infile["body"].decode("utf-8")) as csvfile:
            reader = csv.DictReader(csvfile)
            iuids = [p["IUID"] for p in reader]
        qualifier = self.get_argument("qualifier", None)
        if qualifier not in settings["SITE_LABEL_QUALIFIERS"]:
            qualifier = None
        count = 0
        for iuid in iuids:
            try:
                publication = self.get_publication(iuid)
                if label["value"] in publication["labels"]:
                    raise KeyError
            except KeyError:
                pass
            else:
                with publications.publication.PublicationSaver(
                    publication, rqh=self
                ) as saver:
                    labels = publication["labels"].copy()
                    labels[label["value"]] = qualifier
                    saver["labels"] = labels
                count += 1
        self.set_message_flash(f"Added label to {count} publications.")
        self.see_other("label", label["value"])


class LabelRemove(RequestHandler):
    "Remove a label from a set of publications."

    @tornado.web.authenticated
    def get(self, identifier):
        self.check_admin()
        print(identifier)
        try:
            label = self.get_label(identifier)
        except KeyError as error:
            self.see_other("labels", error=str(error))
            return
        self.render("label/remove.html", label=label["value"])

    @tornado.web.authenticated
    def post(self, identifier):
        self.check_admin()
        try:
            label = self.get_label(identifier)
        except KeyError as error:
            self.see_other("labels", error=str(error))
            return
        try:
            infile = self.request.files["publications"][0]
        except tornado.web.MissingArgumentError:
            self.set_error_flash("no publications subset file provided")
            self.see_other("label", label)
            return
        with io.StringIO(infile["body"].decode("utf-8")) as csvfile:
            reader = csv.DictReader(csvfile)
            iuids = [p["IUID"] for p in reader]
        count = 0
        for iuid in iuids:
            try:
                publication = self.get_publication(iuid)
                if label["value"] not in publication["labels"]:
                    raise KeyError
            except KeyError:
                pass
            else:
                with publications.publication.PublicationSaver(
                    publication, rqh=self
                ) as saver:
                    labels = publication["labels"].copy()
                    labels.pop(label["value"])
                    saver["labels"] = labels
                count += 1
        self.set_message_flash(f"Removed label from {count} publications.")
        self.see_other("label", label["value"])
