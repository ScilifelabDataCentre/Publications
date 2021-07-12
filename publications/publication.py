"Publication pages."

import csv
import io
import logging

import tornado.web
import xlsxwriter

from . import constants
from . import crossref
from . import pubmed
from . import settings
from . import utils
from .saver import Saver, SaverError
from .requesthandler import RequestHandler, ApiMixin


class PublicationSaver(Saver):
    doctype = constants.PUBLICATION

    def initialize(self):
        """Set the initial values for the new document.
        Create the slots with empty starting values;
        allows using 'update' for new instance.
        """
        super().initialize()
        self["title"] = ""
        self["pmid"] = None
        self["doi"] = None
        self["authors"] = []
        self["type"] = None
        self["published"] = None
        self["epublished"] = None
        self["abstract"] = None
        self["journal"] = {}
        self["xrefs"] = []
        self["labels"] = {}
        self["notes"] = None

    def check_published(self, value):
        utils.to_date(value)

    def convert_published(self, value):
        return utils.to_date(value)

    def check_epublished(self, value):
        utils.to_date(value)

    def convert_epublished(self, value):
        if value:
            return utils.to_date(value)
        else:
            return None

    def set_title(self):
        "Set title from form data."
        assert self.rqh, "requires http request context"
        self["title"] = utils.squish(self.rqh.get_argument("title", "") or "[no title]")

    def set_authors(self):
        "Set authors list from form data."
        assert self.rqh, "requires http request context"
        # XXX How to keep associations with researchers!
        authors = []
        for author in self.rqh.get_argument("authors", "").split("\n"):
            author = author.strip()
            if not author: continue
            try:
                family, given = author.split(",", 1)
            except ValueError:  # Name written as 'Per Kraulis'
                parts = author.split()
                family = parts[-1]
                given = " ".join(parts[:-1])
            else:               # Name written as 'Kraulis, Per'
                family = family.strip()
                if not family:
                    family = author
                    given = ""
                given = given.strip()
            initials = "".join([c[0] for c in given.split()])
            authors.append(
                dict(family=family,
                     family_normalized=utils.to_ascii(family).lower(),
                     given=given,
                     given_normalized=utils.to_ascii(given).lower(),
                     initials=initials,
                     initials_normalized=utils.to_ascii(initials).lower()))
        self["authors"] = authors

    def set_researchers(self):
        "Set associations of researcher to author from form data."
        assert self.rqh, "requires http request context"
        for author in self["authors"]:
            name = f"{author['family_normalized']} {author['initials_normalized']}"
            # Remove current association?
            if author.get("researcher"):
                try:
                    if not utils.to_bool(self.rqh.get_argument(name)):
                        author.pop("researcher")
                except tornado.web.MissingArgumentError:
                    pass
            # Set a new association?
            else:
                try:
                    researcher = self.rqh.get_researcher(self.rqh.get_argument(name))
                except (tornado.web.MissingArgumentError, ValueError):
                    pass
                else:
                    author["researcher"] = researcher["_id"]

    def set_pmid_doi(self):
        "Set pmid and doi from form data. No validity checks are made."
        assert self.rqh, "requires http request context"
        self["pmid"] = self.rqh.get_argument("pmid", "") or None
        self["doi"] = self.rqh.get_argument("doi", "") or None

    def set_published(self):
        "Set published and epublished from form data."
        assert self.rqh, "requires http request context"
        self["published"] = self.rqh.get_argument("published", "") or None
        self["epublished"] = self.rqh.get_argument("epublished", "") or None

    def set_open_access(self):
        "Set Open Access flag."
        assert self.rqh, "requires http request context"
        self["open_access"] = utils.to_bool(self.rqh.get_argument("open_access", False))

    def set_journal(self):
        "Set journal from form data."
        assert self.rqh, "requires http request context"
        journal = dict(title=self.rqh.get_argument("journal", "") or None)
        for key in ["issn", "issn-l", "volume", "issue", "pages"]:
            journal[key] = self.rqh.get_argument(key, "") or None
        self["journal"] = journal

    def set_abstract(self):
        "Set abstract from form data."
        assert self.rqh, "requires http request context"
        self["abstract"] = self.rqh.get_argument("abstract", "") or None

    def set_notes(self):
        "Set the notes entry from form data."
        assert self.rqh, "requires http request context"
        self["notes"] = self.rqh.get_argument("notes", "") or None

    def set_qc(self, aspect, flag):
        "Set the QC flag for a given aspect."
        assert self.rqh, "requires http request context"
        if aspect not in settings["PUBLICATION_QC_ASPECTS"]:
            raise ValueError(f"invalid QC aspect '{aspect}'")
        entry = dict(account=self.rqh.current_user["email"],
                     date=utils.today(),
                     flag=bool(flag))
        try:
            self["qc"][aspect] = entry
        except KeyError:
            self["qc"] = {aspect: entry}

    def update(self, other, updated_by_pmid=False):
        """Update a field in the current publication if there is a value 
        in the other publication. It is assumed that they are representations
        of the same source publication.
        Set the 'uppated_by_pmid' flag if True.
        Check if author can be associated with a researcher.
        Create a researcher, if ORCID is available.
        """
        self["title"] = other["title"] or self["title"]
        self["pmid"] = other["pmid"] or self["pmid"]
        self["doi"] = other["doi"] or self["doi"]
        self["type"] = other.get("type") or self.get("type")
        self["published"] = other.get("published") or self.get("published")
        self["epublished"] = other.get("epublished") or self.get("epublished")
        self["abstract"] = other.get("abstract") or self.get("abstract")
        self["xrefs"] = other.get("xrefs") or self.get("xrefs") or []
        if updated_by_pmid:
            self["updated_by_pmid"] = utils.timestamp()

        # Special case for journal field: copy each component field.
        try:
            journal = self["journal"]
        except KeyError:
            self["journal"] = journal = {}
        for key, value in other.get("journal", {}).items():
            if value:
                journal[key] = value

        # Authors: Remember previously associated researchers.
        researchers = {}
        for author in self["authors"]:
            researcher = author.get("researcher")
            if not researcher: continue
            key = "%s %s" % (author["family_normalized"],
                             author["initials_normalized"])
            researchers[key] = researcher
        self["authors"] = other["authors"]
        for author in self["authors"]:
            key = "%s %s" % (author["family_normalized"],
                             author["initials_normalized"])
            try:
                # Previously associated researcher; just set it.
                author["researcher"] = researchers[key]
            except KeyError:
                orcid = author.pop("orcid", None)
                # If ORCID, then associate with researcher.
                if orcid:
                    from publications.researcher import ResearcherSaver
                    # Existing reseacher based on ORCID.
                    try:
                        author["researcher"] = self.rqh.get_researcher(orcid)["_id"]
                    except KeyError:
                        # Create a new researcher.
                        try:
                            with ResearcherSaver(rqh=self.rqh) as saver:
                                saver.set_family(author.get("family"))
                                saver.set_given(author.get("given"))
                                saver.set_initials(author.get("initials"))
                                saver.set_orcid(orcid)
                                saver.set_affiliations(author.get("affiliations"))
                            author["researcher"] = saver.doc["_id"]
                        except ValueError:
                            pass    # Just skip if any problem.
            # Don't save affiliations in publication itself.
            author.pop("affiliations", None)

    def fix_journal(self):
        """Set the appropriate journal title, ISSN and ISSN-L if not done.
        Create the journal entity if it does not exist.
        """
        assert self.rqh, "requires http request context"
        doc = None
        try:
            journal = self["journal"].copy()
        except KeyError:
            journal = {}
        title = journal.get("title")
        issn = journal.get("issn")
        issn_l = journal.get("issn-l")
        if issn:
            try:
                doc = self.rqh.get_doc(issn, "journal/issn")
                issn_l = doc.get("issn-l") or issn_l
            except KeyError:
                try:
                    doc = self.rqh.get_doc(issn, "journal/issn_l")
                    issn_l = issn
                except KeyError:
                    if title:
                        try:
                            doc = self.rqh.get_doc(title, "journal/title")
                        except KeyError:
                            doc = None
                        else:
                            if issn != doc["issn"]:
                                journal["issn"] = doc["issn"]
                                journal["issn-l"] = doc.get("issn-l")
            if doc and title != doc["title"]:
                journal["title"] = doc["title"]
        self["journal"] = journal
        # Create journal entity if it does not exist, and if sufficient data.
        if doc is None and issn and title:
            # Import done here to avoid circularity.
            from publications.journal import JournalSaver
            with JournalSaver(db=self.db) as saver:
                saver["issn"] = issn
                saver["issn-l"] = issn_l
                saver["title"] = title

    def update_labels(self, labels=None, allowed_labels=None, clean=True):
        """Update the labels. If no labels dictionary given, get HTTP form data.
        Only changes the allowed labels for the current user.
        If clean, then remove any missing allowed labels from existing entry.
        """
        if labels is None:
            # Horrible kludge: Unicode issue for labels and qualifiers...
            values = {}
            for key in self.rqh.request.arguments.keys():
                values[utils.to_ascii(key)] =self.rqh.get_argument(key)
            labels = {}
            for label in self.rqh.get_arguments("label"):
                qualifier = values.get(utils.to_ascii(f"{label}_qualifier"))
                if qualifier in settings["SITE_LABEL_QUALIFIERS"]:
                    labels[label] = qualifier
                else:
                    labels[label] = None
        if allowed_labels is None:
            allowed_labels = self.rqh.get_allowed_labels()
        updated = self.get("labels", {}).copy()
        for label in allowed_labels:
            try:
                updated[label] = labels[label]
            except KeyError:
                if clean: updated.pop(label, None)
        self["labels"] = updated


class PublicationMixin:
    "Mixin for access check methods."

    def is_editable(self, publication):
        "Is the publication editable by the current user?"
        if not self.is_curator(): return False
        return True

    def check_editable(self, publication):
        "Check that the publication is editable by the current user."
        if self.is_editable(publication): return
        raise ValueError("You many not edit the publication.")

    def is_xrefs_editable(self, publication):
        "Are the xrefs of the publication editable by the current user?"
        if not self.is_xrefcur(): return False
        return True

    def check_xrefs_editable(self, publication):
        """Check that the xrefs of the publication are editable by
        the current user."""
        if self.is_xrefs_editable(publication): return
        raise ValueError("You many not edit the xrefs of the publication.")

    def is_deletable(self, publication):
        "Is the publication deletable by the current user?"
        if not self.is_curator(): return False
        return True

    def check_deletable(self, publication):
        "Check that the publication is deletable by the current user."
        if self.is_deletable(publication): return
        raise ValueError("You may not delete the publication.")

    def get_allowed_labels(self):
        "Get the set of allowed labels for the account."
        if self.is_admin():
            return set([l["value"] for l in self.get_docs("label/value")])
        else:
            return set(self.current_user["labels"])


class PublicationFetchMixin:
    "Mixin for method to fetch a number of publications from externa sources."

    def fetch(self, identifier, override=False, labels={}, clean=True):
        """Fetch the publication given by identifier (PMID or DOI).
        override: If True, overrides the blacklist.
        labels: Dictionary of labels (key: label, value: qualifier) to set.
                Only allowed labels for the curator are updated.
        clean: Remove any missing allowed labels from an existing entry.
        Raise IOError if no such publication found, or other error.
        Raise KeyError if publication is in the blacklist (and not override).
        """
        self.check_blacklisted(identifier, override=override)

        # Does the publication already exist in the database?
        try:
            current = self.get_publication(identifier)
        except KeyError:
            current = None

        # Fetch from external source according to identifier type.
        identifier_is_pmid = constants.PMID_RX.match(identifier)
        if identifier_is_pmid:
            try:
                new = pubmed.fetch(identifier,
                                   timeout=settings["PUBMED_TIMEOUT"],
                                   delay=settings["PUBMED_DELAY"],
                                   api_key=settings["NCBI_API_KEY"])
            except IOError:
                msg = f"No response from PubMed for {identifier}."
                if current:
                    msg += " Publication exists, but could not be updated."
                raise IOError(msg)
            except ValueError as error:
                raise IOError(f"{identifier}, {error}")

        else: # Not PMID, assume DOI identifier.
            try:
                new = crossref.fetch(identifier,
                                     timeout=settings["CROSSREF_TIMEOUT"],
                                     delay=settings["CROSSREF_DELAY"])
            except IOError:
                msg = f"No response from Crossref for {identifier}."
                if current:
                    msg += " Publication exists, but could not be updated."
                raise IOError(msg)
            except ValueError as error:
                raise IOError(f"{identifier}, {error}")

        # Check blacklist registry again; other external id may be there.
        self.check_blacklisted(new.get("pmid"), override=override)
        self.check_blacklisted(new.get("doi"), override=override)

        # Find the current entry again by the other identifier.
        if current is None:
            # Maybe the publication has been fetched using the other identifier?
            if identifier_is_pmid:
                try:
                    current = self.get_publication(new.get("doi"))
                except KeyError:
                    pass
            else:
                try:
                    current = self.get_publication(new.get("pmid"))
                except KeyError:
                    pass

        # Update the current entry, if it exists.
        if current:
            with PublicationSaver(current, rqh=self) as saver:
                saver.update(new, updated_by_pmid=identifier_is_pmid)
                saver.fix_journal()
                saver.update_labels(labels=labels, clean=clean)
            return current
        # Else create a new entry.
        else:
            with PublicationSaver(rqh=self) as saver:
                saver.update(new, updated_by_pmid=identifier_is_pmid)
                saver.fix_journal()
                saver.update_labels(labels=labels)
            return saver.doc

    def check_blacklisted(self, identifier, override=False):
        """Raise KeyError if identifier blacklisted.
        If override, remove from blacklist.
        """
        blacklisted = self.get_blacklisted(identifier)
        if blacklisted:
            if override:
                self.db.delete(blacklisted)
            else:
                raise KeyError(identifier)


class Publication(PublicationMixin, RequestHandler):
    "Display the publication."

    def get(self, identifier):
        "Display the publication."
        try:
            publication = self.get_publication(identifier)
        except KeyError as error:
            self.see_other("home", error=str(error))
            return
        self.render("publication.html",
                    publication=publication,
                    is_editable=self.is_editable(publication),
                    is_xrefs_editable=self.is_xrefs_editable(publication),
                    is_deletable=self.is_deletable(publication))

    @tornado.web.authenticated
    def post(self, identifier):
        if self.get_argument("_http_method", None) == "delete":
            self.delete(identifier)
            return
        raise tornado.web.HTTPError(405, reason="POST only allowed for DELETE")

    @tornado.web.authenticated
    def delete(self, identifier):
        try:
            publication = self.get_publication(identifier)
            self.check_deletable(publication)
        except (KeyError, ValueError) as error:
            self.see_other("home", error=str(error))
            return
        # Delete log entries
        for log in self.get_logs(publication["_id"]):
            self.db.delete(log)
        self.db.delete(publication)
        self.see_other("home")


class PublicationJson(PublicationMixin, RequestHandler):
    "Publication JSON data."

    def get(self, identifier):
        "Display the publication."
        try:
            publication = self.get_publication(identifier)
        except KeyError as error:
            raise tornado.web.HTTPError(404, reason="no such publication")
        self.write(self.get_publication_json(publication, single=True))


class Publications(RequestHandler):
    "Publications list display page."

    TEMPLATE = "publications.html"

    def get(self, year=None):
        limit = self.get_limit()
        if year:
            kwargs = dict(key=year)
            if limit:
                kwargs["limit"] = limit
            publications = self.get_docs("publication/year", **kwargs)
            publications.sort(key=lambda i: i["published"], reverse=True)
        else:
            kwargs = dict(key=constants.CEILING, last="", descending=True)
            if limit:
                kwargs["limit"] = limit
            publications = self.get_docs("publication/published", **kwargs)
        self.render(self.TEMPLATE,
                    publications=publications,
                    year=year,
                    limit=limit)


class PublicationsTable(Publications):
    "Publications table display page."

    TEMPLATE = "publications_table.html"


class PublicationsJson(Publications):
    "Publications JSON output."

    def render(self, template, **kwargs):
        "Override; ignores template, and outputs JSON instead of HTML."
        URL = self.absolute_reverse_url
        publications = kwargs["publications"]
        result = dict()
        result["entity"] = "publications"
        result["timestamp"] = utils.timestamp()
        year = kwargs["year"]
        if year:
            result["year"] = year
        result["links"] = links = dict()
        if year:
            links["self"] = {"href": URL("publications_year_json", year)}
            links["display"] = {"href": URL("publications_year", year)}
        else:
            links["self"] = {"href": URL("publications_json")}
            links["display"] = {"href": URL("publications")}
        if kwargs["limit"]:
            result["limit"] = kwargs["limit"]
        result["publications_count"] = len(publications)
        full = utils.to_bool(self.get_argument("full", True))
        result["full"] = full
        result["publications"] = [self.get_publication_json(publ, full=full)
                                  for publ in publications]
        self.write(result)


class FilterMixin:
    "Method for getting publications filtered by form arguments."

    def get_filtered_publications(self):
        "Get the publications filtered according to form arguments."
        result = []
        # By years.
        years = self.get_arguments("years")
        if years:
            for year in years:
                result.extend(self.get_docs("publication/year", key=year))
        # All publications.
        else:
            result = self.get_docs("publication/published",
                                   key=constants.CEILING,
                                   last="",
                                   descending=True)
        # Filter by labels if any given.
        labels = set(self.get_arguments("labels"))
        if labels:
            kept = []
            for publication in result:
                for label in publication.get("labels", {}):
                    if label in labels:
                        kept.append(publication)
                        break
            result = kept

        # Filter by active labels during a year.
        active = self.get_argument("active", "")
        if settings["TEMPORAL_LABELS"] and active:
            if active.lower() == "current":
                labels = set([d["value"] 
                              for d in self.get_docs("label/current")])
            else:
                labels = set()
                for label in self.get_docs("label/value"):
                    started = label.get("started")
                    if started and started <= active: # Year as str
                        ended = label.get("ended")
                        if ended:
                            if active <= ended: # Year as str
                                labels.add(label["value"])
                        else:
                            labels.add(label["value"])
            for publication in result:
                publication["labels"] = dict([(k, publication["labels"][k]) 
                                              for k in publication["labels"]
                                              if k in labels])
            result = [p for p in result if p["labels"]]

        result.sort(key=lambda p: p.get("published"), reverse=True)
        return result


class ParametersMixin:
    "Method for setting output parameters by form arguments."

    def set_parameters(self):
        "Set output parameters. Some may not apply to the output format."
        self.single_label = utils.to_bool(
            self.get_argument("single_label", "false"))
        self.all_authors = utils.to_bool(
            self.get_argument("all_authors", "false"))
        self.output_issn = utils.to_bool(self.get_argument("issn", "false"))
        if settings["TEMPORAL_LABELS"]:
            self.temporal_label = self.get_argument("temporal_label", "") or None
        else:
            self.temporal_label = None
        self.numbered = utils.to_bool(self.get_argument("numbered", "false"))
        self.doi_url= utils.to_bool(self.get_argument("doi_url", "false"))
        self.pmid_url= utils.to_bool(self.get_argument("pmid_url", "false"))
        try:
            self.maxline = self.get_argument("maxline", None)
            if self.maxline:
                self.maxline = int(self.maxline)
                if self.maxline <= 20: raise ValueError
        except (ValueError, TypeError):
            self.maxline = None


class TabularWriteMixin(ParametersMixin):
    "Abstract writer of publications in tabular form. For CSV and XLSX output."

    def write_publications(self, publications):
        "Collect output parameters and produce output."
        self.set_parameters()
        row = ["Title",
               "Authors",
               "Journal"]
        if self.output_issn:
            row.append("ISSN")
            row.append("ISSN-L")
            label_pos = 13
        else:
            label_pos = 11
        row.extend(
            ["Year", 
             "Published",
             "E-published",
             "Volume",
             "Issue",
             "Pages",
             "DOI",
             "PMID",
             "Labels",
             "Qualifiers",
             "IUID",
             "URL",
             "DOI URL",
             "PubMed URL",
             "QC",
            ])
        self.write_header(row)
        for publication in publications:
            year = publication.get("published")
            if year:
                year = year.split("-")[0]
            journal = publication.get("journal") or {}
            pmid = publication.get("pmid")
            if pmid:
                pubmed_url = constants.PUBMED_URL % pmid
            else:
                pubmed_url = ""
            doi_url = publication.get("doi")
            if doi_url:
                doi_url = constants.DOI_URL % doi_url
            row = [
                publication.get("title"),
                utils.get_formatted_authors(publication["authors"],
                                            complete=self.all_authors),
                journal.get("title")]
            if self.output_issn:
                row.append(journal.get("issn"))
                row.append(self.get_issn_l(journal.get("issn")))
            qc = "|".join(["%s:%s" % (k, v["flag"]) for 
                           k, v in publication.get("qc", {}).items()])
            row.extend(
                [year,
                 publication.get("published"),
                 publication.get("epublished"),
                 journal.get("volume"),
                 journal.get("issue"),
                 journal.get("pages"),
                 publication.get("doi"),
                 publication.get("pmid"),
                 "",            # label_pos, see above; fixed below
                 "",            # label_pos+1, see above; fixed below
                 publication["_id"],
                 self.absolute_reverse_url("publication", publication["_id"]),
                 doi_url,
                 pubmed_url,
                 qc,
                ]
            )
            # Labels to output: single per row, or concatenated.
            labels = sorted(list(publication.get("labels", {}).items()))
            if self.single_label:
                for label, qualifier in labels:
                    row[label_pos] = label
                    row[label_pos+1] = qualifier
                    self.write_row(row)
            else:
                row[label_pos] = "|".join([l[0] for l in labels])
                row[label_pos+1] = "|".join([l[1] or "" for l in labels])
                self.write_row(row)

    def write_header(self, row):
        "To be implemented by the inheriting subclass."
        raise NotImplementedError

    def write_row(self, row):
        "To be implemented by the inheriting subclass."
        raise NotImplementedError


class PublicationsCsv(FilterMixin, TabularWriteMixin, Publications):
    "Publications CSV output."

    def get(self):
        "Show output selection page."
        self.render("publications_csv.html",
                    year=self.get_argument("year", None),
                    labels=set(self.get_arguments("label")),
                    all_labels=sorted([l["value"]
                                       for l in self.get_docs("label/value")]),
                    cancel_url=self.get_argument("cancel_url", None))

    # Authentication is *not* required!
    def post(self):
        "Produce CSV output."
        delimiter = self.get_argument("delimiter", "").lower()
        if delimiter == "comma":
            delimiter = ","
        elif delimiter == "semi-colon":
            delimiter = ";"
        else:
            delimiter = ","
        self.csvbuffer = io.StringIO()
        self.writer = csv.writer(self.csvbuffer,
                                 delimiter=delimiter,
                                 quoting=csv.QUOTE_NONNUMERIC)
        self.write_publications(self.get_filtered_publications())
        value = self.csvbuffer.getvalue()
        if self.get_argument("encoding", "").lower() == "iso-8859-1":
            value = value.encode("iso-8859-1", "ignore")
        self.write(value)
        self.set_header("Content-Type", constants.CSV_MIME)
        self.set_header("Content-Disposition", 
                        'attachment; filename="publications.csv"')

    def write_header(self, row):
        "Write the XLSX header row."
        self.write_row(row)

    def write_row(self, row):
        "Write a CSV data row."
        for pos, value in enumerate(row):
            if isinstance(value, str):
                # Remove CR characters; keep newline.
                value = value.replace("\r", "")
                # Remove any beginning potentially dangerous character '=-+@'.
                # See http://georgemauer.net/2017/10/07/csv-injection.html
                while len(value) and value[0] in "=-+@":
                    value = value[1:]
                row[pos] = value
        self.writer.writerow(row)


class PublicationsXlsx(FilterMixin, TabularWriteMixin, Publications):
    "Publications XLSX output."

    def get(self):
        "Show output selection page."
        self.render("publications_xlsx.html",
                    year=self.get_argument("year", None),
                    labels=set(self.get_arguments("label")),
                    all_labels=sorted([l["value"]
                                       for l in self.get_docs("label/value")]),
                    cancel_url=self.get_argument("cancel_url", None))

    # Authentication is *not* required!
    def post(self):
        "Produce XLSX output."
        self.xlsxbuffer = io.BytesIO()
        self.workbook = xlsxwriter.Workbook(self.xlsxbuffer,
                                            {"in_memory": True})
        self.ws = self.workbook.add_worksheet("Publications")
        self.write_publications(self.get_filtered_publications())
        self.workbook.close()
        self.xlsxbuffer.seek(0)
        self.write(self.xlsxbuffer.getvalue())
        self.set_header("Content-Type", constants.XLSX_MIME)
        self.set_header("Content-Disposition", 
                        'attachment; filename="publications.xlsx"')

    def write_header(self, row):
        "Write the XLSX header row."
        self.ws.freeze_panes(1, 0)
        self.ws.set_row(0, None, self.workbook.add_format({"bold": True}))
        self.ws.set_column(0, 1, 40) # Title
        self.ws.set_column(2, 2, 20) # Authors
        self.ws.set_column(3, 3, 10) # Journal
        if self.output_issn:
            self.ws.set_column(11, 11, 30) # DOI
            self.ws.set_column(12, 12, 10) # PMID
            self.ws.set_column(13, 13, 30) # Labels
            self.ws.set_column(14, 15, 20) # Qualifiers, IUID
        else:
            self.ws.set_column(9, 9, 30) # DOI
            self.ws.set_column(10, 10, 10) # PMID
            self.ws.set_column(11, 11, 30) # Labels
            self.ws.set_column(12, 13, 20) # Qualifiers, IUID
        self.x = 0
        self.write_row(row)

    def write_row(self, row):
        "Write an XLSX data row."
        for y, item in enumerate(row):
            if isinstance(item, str): # Remove CR characters; keep newline.
                self.ws.write(self.x, y, item.replace("\r", ""))
            else:
                self.ws.write(self.x, y, item)
        self.x += 1


class PublicationsTxt(FilterMixin, ParametersMixin, Publications):
    "Publications text file output."

    def get(self):
        "Show output selection page."
        self.render("publications_txt.html",
                    year=self.get_argument("year", None),
                    labels=set(self.get_arguments("label")),
                    all_labels=sorted([l["value"]
                                       for l in self.get_docs("label/value")]),
                    cancel_url=self.get_argument("cancel_url", None))

    # Authentication is *not* required!
    def post(self):
        "Produce TXT output."
        publications = self.get_filtered_publications()
        self.set_parameters()
        self.text = io.StringIO()
        for number, publication in enumerate(publications, 1):
            if self.numbered:
                self.line = f"{number}."
                self.indent = " " * (len(self.line) + 1)
            else:
                self.line = ""
                self.indent = ""
            authors = utils.get_formatted_authors(publication["authors"],
                                                  complete=self.all_authors)
            self.write_fragment(authors, comma=False)
            self.write_fragment(f'"{publication.get("title")}"')
            journal = publication.get("journal") or {}
            self.write_fragment(journal.get("title") or "")
            year = publication.get("published")
            if year:
                year = year.split("-")[0]
            self.write_fragment(year)
            if journal.get("volume"):
                self.write_fragment(journal["volume"])
            if journal.get("issue"):
                self.write_fragment(f"({journal['issue']})", comma=False)
            if journal.get("pages"):
                self.write_fragment(journal["pages"])
            if self.doi_url:
                doi_url = publication.get("doi")
                if doi_url:
                    self.write_fragment(constants.DOI_URL % doi_url)
            if self.pmid_url:
                pmid_url = publication.get("pmid")
                if pmid_url:
                    self.write_fragment(constants.PUBMED_URL % pmid_url)
            if self.line:
                self.text.write(self.line)
                self.text.write("\n")
            self.text.write("\n")
        value = self.text.getvalue()
        self.write(value)
        self.set_header("Content-Type", constants.TXT_MIME)
        self.set_header("Content-Disposition", 
                        'attachment; filename="publications.txt"')

    def write_fragment(self, fragment, comma=True):
        "Write the given fragment to the line."
        if comma:
            self.line += ","
        parts = fragment.split()
        for part in parts:
            length = len(self.line) + len(part) + 1
            if self.maxline is not None and length > self.maxline:
                self.text.write(self.line + "\n")
                self.line = self.indent + part
            else:
                if self.line:
                    self.line += " "
                self.line += part


class PublicationsNoPmid(PublicationMixin, RequestHandler):
    "Publications lacking PMID."

    def get(self):
        publications = self.get_docs("publication/no_pmid")
        for publication in publications:
            publication["pmid_findable"] = self.is_editable(publication) and \
                                           publication.get("doi")
        # Put the publications first for which there is a DOI, making PMID
        # findable, and for which find has not been attempted
        publs1 = []
        publs2 = []
        publs3 = []
        for publ in publications:
            if publ["pmid_findable"]:
                if publ.get("no_pmid_found"):
                    publs2.append(publ)
                else:
                    publs1.append(publ)
            else:
                publs3.append(publ)
        publs1.sort(key=lambda p: p["modified"])
        publs2.sort(key=lambda p: p["modified"])
        publs3.sort(key=lambda p: p["modified"])
        publications = publs1 + publs2 + publs3
        self.render("publications_no_pmid.html", publications=publications)


class PublicationsNoPmidJson(PublicationsNoPmid):
    "Publications lacking PMID JSON output."

    def render(self, template, **kwargs):
        "Override; ignores template, and outputs JSON instead of HTML."
        URL = self.absolute_reverse_url
        publications = kwargs["publications"]
        result = dict()
        result["entity"] = "publications_no_pmid"
        result["timestamp"] = utils.timestamp()
        result["links"] = links = dict()
        links["self"] = {"href": URL("publications_no_pmid_json")}
        links["display"] = {"href": URL("publications_no_pmid")}
        result["publications_count"] = len(publications)
        result["publications"] = [self.get_publication_json(publ)
                                  for publ in publications]
        self.write(result)


class PublicationsNoDoi(RequestHandler):
    "Publications lacking DOI."

    def get(self):
        publications = self.get_docs("publication/no_doi")
        publications.sort(key=lambda p: p["modified"])
        self.render("publications_no_doi.html", publications=publications)


class PublicationsNoDoiJson(PublicationsNoDoi):
    "Publications lacking DOI JSON output."

    def render(self, template, **kwargs):
        "Override; ignores template, and outputs JSON instead of HTML."
        URL = self.absolute_reverse_url
        publications = kwargs["publications"]
        result = dict()
        result["entity"] = "publications_no_doi"
        result["timestamp"] = utils.timestamp()
        result["links"] = links = dict()
        links["self"] = {"href": URL("publications_no_doi_json")}
        links["display"] = {"href": URL("publications_no_doi")}
        result["publications_count"] = len(publications)
        result["publications"] = [self.get_publication_json(publ)
                                  for publ in publications]
        self.write(result)


class PublicationsNoLabel(RequestHandler):
    "Publications lacking label."

    def get(self):
        publications = []
        for publication in self.get_docs("publication/modified", descending=True):
            if not publication.get("labels"):
                publications.append(publication)
        self.render("publications_no_label.html", publications=publications)


class PublicationsNoLabelJson(PublicationsNoLabel):
    "Publications lacking label JSON output."

    def render(self, template, **kwargs):
        "Override; ignores template, and outputs JSON instead of HTML."
        URL = self.absolute_reverse_url
        publications = kwargs["publications"]
        result = dict()
        result["entity"] = "publications_no_label"
        result["timestamp"] = utils.timestamp()
        result["links"] = links = dict()
        links["self"] = {"href": URL("publications_no_label_json")}
        links["display"] = {"href": URL("publications_no_label")}
        result["publications_count"] = len(publications)
        full = utils.to_bool(self.get_argument("full", True))
        result["full"] = full
        result["publications"] = [self.get_publication_json(publ, full=full)
                                  for publ in publications]
        self.write(result)


class PublicationsDuplicates(RequestHandler):
    """Apparently duplicated publications.
    First find 4 longest words in the title, and make a lookup key of them.
    Use this to identify possible duplicates.
    Also check whether the first 4 author family names match.
    Some false positives are expected.
    """

    def get(self):
        lookup = {}             # Key: 4 longest words in title
        duplicates = []
        for publ1 in self.get_docs("publication/modified"):
            title = utils.to_ascii(publ1["title"], alphanum=True).lower()
            parts = sorted(title.split(), key=len, reverse=True)
            key = " ".join(parts[:4])
            try:
                publ2 = lookup[key]
                for auth1, auth2 in zip(publ1["authors"][:4],
                                        publ2["authors"][:4]):
                    if auth1["family_normalized"] != auth2["family_normalized"]:
                        break
                else:
                    duplicates.append((publ1, publ2))
            except KeyError:
                lookup[key] = publ1
        self.render("publications_duplicates.html", duplicates=duplicates)


class PublicationsModified(PublicationMixin, RequestHandler):
    "List of most recently modified publications."

    def get(self):
        self.check_curator()
        kwargs = dict(descending=True,
                      limit=self.get_limit(settings["LONG_PUBLICATIONS_LIST_LIMIT"]))
        docs = self.get_docs("publication/modified", **kwargs)
        self.render("publications_modified.html", publications=docs)


class PublicationAdd(PublicationMixin, RequestHandler):
    "Add a publication by hand."

    @tornado.web.authenticated
    def get(self):
        self.check_curator()
        self.render("publication_add.html", labels=self.get_allowed_labels())

    @tornado.web.authenticated
    def post(self):
        self.check_curator()
        with PublicationSaver(rqh=self) as saver:
            saver.set_title()
            saver.set_authors()
            saver.set_pmid_doi()
            saver.set_published()
            saver.set_journal()
            saver.set_abstract()
            saver.update_labels()
            publication = saver.doc
        self.see_other("publication", publication["_id"])


class PublicationFetch(PublicationFetchMixin, PublicationMixin, RequestHandler):
    "Fetch publication(s) given list of DOIs or PMIDs."

    @tornado.web.authenticated
    def get(self):
        self.check_curator()
        fetched = self.get_cookie("fetched", None)
        self.clear_cookie("fetched")
        docs = []
        if fetched:
            for iuid in fetched.split("_"):
                try:
                    docs.append(self.get_doc(iuid))
                except KeyError:
                    pass
        checked_labels = dict()
        labels_arg = self.get_argument("labels", "")
        if labels_arg:
            for label in labels_arg.split("|"):
                parts = label.split("/")
                if len(parts) == 1:
                    checked_labels[parts[0]] = None
                elif len(parts) > 1:
                    checked_labels[parts[0]] = "/".join(parts[1:])
        labels = self.get_allowed_labels()
        # If curator for only a small number of labels (see settings),
        # then check them to start with. Otherwise let be unchecked.
        if not checked_labels and \
           self.current_user["role"] == constants.CURATOR and \
           len(labels) <= settings["MAX_NUMBER_LABELS_PRECHECKED"]:
            for label in labels:
                checked_labels[label] = None
        self.render("publication_fetch.html", 
                    labels=labels,
                    checked_labels=checked_labels,
                    publications=docs)

    @tornado.web.authenticated
    def post(self):
        self.check_curator()
        identifiers = self.get_argument("identifiers", "").split()
        identifiers = [utils.strip_prefix(i) for i in identifiers]
        identifiers = [i for i in identifiers if i]
        override = utils.to_bool(self.get_argument("override", False))
        labels = {}
        for label in self.get_arguments("label"):
            labels[label] = self.get_argument(f"{label}_qualifier", None)

        errors = []
        blacklisted = []
        fetched = set()
        existing = set()
        for identifier in identifiers:
            # Skip if number of loaded publications reached the limit
            if len(fetched) >= settings["PUBLICATIONS_FETCHED_LIMIT"]: break

            try:
                publ = self.fetch(identifier, override=override, labels=labels,
                                  clean=not self.is_admin())
            except IOError as error:
                errors.append(str(error))
            except KeyError as error:
                blacklisted.append(str(error))
            else:
                fetched.add(publ["_id"])

        self.set_cookie("fetched", "_".join(fetched))
        kwargs = {"message": f"{len(fetched)} publication(s) fetched."}
        kwargs["labels"] = "|".join([f"{label}/{qualifier}" if qualifier 
                                     else label
                                     for label, qualifier in labels.items()])
        if errors:
            kwargs["error"] = constants.FETCH_ERROR + ", ".join(errors)
        if blacklisted:
            kwargs["message"] += " " + constants.BLACKLISTED_MESSAGE + \
                                 ", ".join(blacklisted)
        self.see_other("publication_fetch", **kwargs)


class PublicationEdit(PublicationMixin, RequestHandler):
    "Edit the publication."

    @tornado.web.authenticated
    def get(self, iuid):
        try:
            publication = self.get_publication(iuid)
            self.check_editable(publication)
        except (KeyError, ValueError) as error:
            self.see_other("home", error=str(error))
            return
        self.render("publication_edit.html",
                    publication=publication,
                    labels=self.get_allowed_labels())

    @tornado.web.authenticated
    def post(self, iuid):
        try:
            publication = self.get_publication(iuid)
            self.check_editable(publication)
        except (KeyError, ValueError) as error:
            self.see_other("home", error=str(error))
            return
        try:
            with PublicationSaver(doc=publication, rqh=self) as saver:
                saver.check_revision()
                saver.set_title()
                saver.set_authors()
                saver.set_pmid_doi()
                saver.set_published()
                saver.set_open_access()
                saver.set_journal()
                saver.set_abstract()
                saver.update_labels()
                saver.set_notes()
        except SaverError:
            self.set_error_flash(utils.REV_ERROR)
        self.see_other("publication", publication["_id"])


class PublicationResearchers(PublicationMixin, RequestHandler):
    "Edit the publication's associations with researchers."

    @tornado.web.authenticated
    def get(self, iuid):
        try:
            publication = self.get_publication(iuid)
            self.check_editable(publication)
        except (KeyError, ValueError) as error:
            self.see_other("home", error=str(error))
            return
        for author in publication["authors"]:
            if not author.get("researcher"):
                author["researchers"] = self.get_researchers(
                    author["family"], initials=author["initials"])
        self.render("publication_researchers.html",
                    publication=publication)

    @tornado.web.authenticated
    def post(self, iuid):
        try:
            publication = self.get_publication(iuid)
            self.check_editable(publication)
        except (KeyError, ValueError) as error:
            self.see_other("home", error=str(error))
            return
        try:
            with PublicationSaver(doc=publication, rqh=self) as saver:
                saver.check_revision()
                saver.set_researchers()
        except SaverError:
            self.set_error_flash(utils.REV_ERROR)
        self.see_other("publication", publication["_id"])


class PublicationXrefs(PublicationMixin, RequestHandler):
    "Edit the publication database references, including plain URLs."

    @tornado.web.authenticated
    def get(self, iuid):
        try:
            publication = self.get_publication(iuid)
            self.check_xrefs_editable(publication)
        except (KeyError, ValueError) as error:
            self.see_other("home", error=str(error))
            return
        self.render("publication_xrefs.html", publication=publication)

    @tornado.web.authenticated
    def post(self, iuid):
        try:
            publication = self.get_publication(iuid)
            self.check_xrefs_editable(publication)
        except (KeyError, ValueError) as error:
            self.see_other("home", error=str(error))
            return
        try:
            with PublicationSaver(doc=publication, rqh=self) as saver:
                saver.check_revision()
                db = self.get_argument("db_other", None)
                if not db:
                    db = self.get_argument("db", None)
                if not db: raise ValueError("No db given.")
                key = self.get_argument("key")
                if not key: raise ValueError("No accession (key) given.")
                description = self.get_argument("description", None) or None
                xrefs = publication.get("xrefs", [])[:] # Copy of list
                if self.get_argument("_http_method", None) == "DELETE":
                    saver["xrefs"] = [x for x in xrefs
                                      if (x["db"].lower() != db.lower() or
                                          x["key"] != key)]
                else:
                    for xref in xrefs: # Update description if already there.
                        if xref["db"].lower() == db.lower() and \
                           xref["key"] == key:
                            xref["description"] = description
                            break
                    else:
                        xrefs.append(dict(db=db,
                                          key=key,
                                          description=description))
                    saver["xrefs"] = xrefs
        except SaverError:
            self.set_error_flash(utils.REV_ERROR)
        except (tornado.web.MissingArgumentError, ValueError) as error:
            self.set_error_flash(str(error))
        if self.get_argument("__save__", "") == "continue":
            self.see_other("publication_xrefs", publication["_id"])
        else:
            self.see_other("publication", publication["_id"])


class PublicationBlacklist(PublicationMixin, RequestHandler):
    "Blacklist a publication and record its external identifiers."

    @tornado.web.authenticated
    def post(self, identifier):
        try:
            publication = self.get_publication(identifier)
            self.check_deletable(publication)
        except (KeyError, ValueError) as error:
            self.see_other("home", error=str(error))
            return
        blacklist = {constants.DOCTYPE: constants.BLACKLIST,
                     "title": publication["title"],
                     "pmid": publication.get("pmid"),
                     "doi": publication.get("doi"),
                     "created": utils.timestamp(),
                     "owner": self.current_user["email"]}
        self.db[utils.get_iuid()] = blacklist
        self.delete_entity(publication)
        try:
            self.redirect(self.get_argument("next"))
        except tornado.web.MissingArgumentError:
            self.see_other("home")


class ApiPublicationFetch(PublicationFetchMixin, PublicationMixin,
                          ApiMixin, RequestHandler):
    "Fetch a publication given its PMID or DOI."

    @tornado.web.authenticated
    def post(self):
        self.check_curator()
        data = self.get_json_body()
        try:
            identifier = data["identifier"]
        except KeyError:
            raise tornado.web.HTTPError(400, reason="no identifier given")
        try:
            publ = self.fetch(identifier,
                              override=bool(data.get("override")),
                              labels=data.get("labels", {}))
        except IOError as error:
            raise tornado.web.HTTPError(400, reason=str(error))
        except KeyError as error:
            raise tornado.web.HTTPError(409, reason=f"blacklisted {error}")
        self.write(
            dict(iuid=publ["_id"],
                 href=self.absolute_reverse_url("publication", publ["_id"])))


class PublicationQc(PublicationMixin, RequestHandler):
    "Set the QC aspect flag for the publication."

    @tornado.web.authenticated
    def post(self, identifier):
        try:
            publication = self.get_publication(identifier)
        except (KeyError, ValueError) as error:
            self.see_other("home", error=str(error))
            return
        try:
            aspect = self.get_argument("aspect")
            flag = utils.to_bool(self.get_argument("flag", False))
            with PublicationSaver(publication, rqh=self) as saver:
                saver.set_qc(aspect, flag)
        except (tornado.web.MissingArgumentError, ValueError) as error:
            self.set_error_flash(str(error))
        self.see_other("publication", identifier)


class PublicationUpdatePmid(PublicationMixin, RequestHandler):
    """Update the publication by data from PubMed.
    Same action as fetching an already existing publication.
    """

    @tornado.web.authenticated
    def post(self, iuid):
        try:
            publication = self.get_publication(iuid)
        except KeyError as error:
            self.see_other("home", error=str(error))
            return
        try:
            self.check_editable(publication)
            identifier = publication.get("pmid")
            if not identifier:
                raise KeyError("no PMID for publication")
        except (KeyError, ValueError) as error:
            self.see_other("publication", publication["_id"], error=str(error))
            return
        try:
            new = pubmed.fetch(identifier,
                               timeout=settings["PUBMED_TIMEOUT"],
                               delay=settings["PUBMED_DELAY"],
                               api_key=settings["NCBI_API_KEY"])
        except (OSError, IOError):
            self.see_other("publication", publication["_id"],
                           error=f"No response from PubMed for {identifier}.")
            return
        except ValueError as error:
            self.see_other("publication", publication["_id"],
                           error=f"{identifier}, {error}")
            return
        with PublicationSaver(doc=publication, rqh=self) as saver:
            saver.update(new, updated_by_pmid=True)
            saver.fix_journal()
        self.see_other("publication", publication["_id"],
                       message="Updated from PubMed.")


class PublicationFindPmid(PublicationMixin, RequestHandler):
    "Given DOI, try to locate publication at PubMed and set PMID."

    @tornado.web.authenticated
    def post(self, iuid):
        try:
            publication = self.get_publication(iuid)
        except KeyError as error:
            self.see_other("home", error=str(error))
            return
        try:
            self.check_editable(publication)
            identifier = publication.get("doi")
            if not identifier:
                raise ValueError("no DOI for publication")
        except KeyError as error:
            self.see_other("publication", publication["_id"], error=str(error))
            return
        try:
            try:
                found = pubmed.search(doi=identifier,
                                      timeout=settings["PUBMED_TIMEOUT"],
                                      delay=settings["PUBMED_DELAY"],
                                      api_key=settings["NCBI_API_KEY"])
                if len(found) == 0: 
                    raise ValueError("No PubMed entry found")
                if len(found) > 1:
                    raise ValueError("More than one PubMed entry found")
            except (OSError, IOError):
                raise ValueError(f"No response from PubMed for {identifier}.")
            except ValueError as error:
                with PublicationSaver(doc=publication, rqh=self) as saver:
                    saver["no_pmid_found"] = utils.timestamp()
                raise ValueError(f"{identifier}, {error}")
            with PublicationSaver(doc=publication, rqh=self) as saver:
                saver["pmid"] = found[0]

        except ValueError as error:
            self.set_error_flash(str(error))
        self.see_other("publication", publication["_id"])


class PublicationUpdateDoi(PublicationMixin, RequestHandler):
    """Update the publication by data from Crossref.
    Same action as fetching an already existing publication.
    """

    @tornado.web.authenticated
    def post(self, iuid):
        try:
            publication = self.get_publication(iuid)
        except KeyError as error:
            self.see_other("home", error=str(error))
            return
        try:
            self.check_editable(publication)
            identifier = publication.get("doi")
            if not identifier:
                raise KeyError("no DOI for publication")
        except (KeyError, ValueError) as error:
            self.see_other("publication", publication["_id"], error=str(error))
            return
        try:
            new = crossref.fetch(identifier,
                                 timeout=settings["CROSSREF_TIMEOUT"],
                                 delay=settings["CROSSREF_DELAY"])
        except (OSError, IOError):
            self.see_other("publication", publication["_id"],
                           error=f"No response from Crossref for {identifier}.")
            return
        except ValueError as error:
            self.see_other("publication", publication["_id"],
                           error=f"{identifier}, {error}")
            return
        with PublicationSaver(doc=publication, rqh=self) as saver:
            saver.update(new)
            saver.fix_journal()
        self.see_other("publication", publication["_id"],
                       message="Updated from Crossref.")
