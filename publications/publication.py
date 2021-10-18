"Publication pages."

import functools
import logging

import couchdb2
import tornado.web

from publications import constants
from publications import crossref
from publications import pubmed
from publications import settings
from publications import utils
from publications.saver import Saver, SaverError
from publications.subset import Subset
from publications.writer import CsvWriter, XlsxWriter, TextWriter
from publications.requesthandler import RequestHandler, ApiMixin


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
        # Authors: Transfer previously associated researchers.
        researchers = self._get_researchers()
        for author in authors:
            key = "%s %s" % (author["family_normalized"],
                             author["initials_normalized"])
            try:
                author["researcher"] = researchers[key]
            except KeyError:
                pass
        self["authors"] = authors

    def _get_researchers(self):
        "Get the current assocations of author to researcher."
        result = {}
        for author in self.doc["authors"]:
            researcher = author.get("researcher")
            if not researcher: continue
            key = "%s %s" % (author["family_normalized"],
                             author["initials_normalized"])
            result[key] = researcher
        return result

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

    def update(self, other, updated_by_pmid=False):
        """Update a field in the current publication if there is a value 
        in the other publication. It is assumed that they are representations
        of the same source publication.
        Set the 'uppated_by_pmid' flag if True.
        Check if author can be associated with a researcher.
        Create a researcher, if ORCID is available.
        """
        # Import done here to avoid circularity.
        from publications.researcher import ResearcherSaver
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

        # Authors: Transfer previously associated researchers.
        researchers = self._get_researchers()
        self["authors"] = other["authors"]
        # Transfer the researcher association, if any.
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
        # Import done here to avoid circularity.
        from publications.journal import JournalSaver
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
                doc = utils.get_doc(self.db, "journal", "issn", issn)
                issn_l = doc.get("issn-l") or issn_l
            except KeyError:
                try:
                    doc = utils.get_doc(self.db, "journal", "issn_l", issn)
                    issn_l = issn
                except KeyError:
                    if title:
                        try:
                            doc = utils.get_doc(self.db, "journal", "title", title)
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
            with JournalSaver(db=self.db) as saver:
                saver["issn"] = issn
                saver["issn-l"] = issn_l
                saver["title"] = title

    def update_labels(self, labels=None, allowed_labels=None, clean=True):
        """Update the labels. If no labels dictionary given, get HTTP form data.
        Only changes the allowed labels for the current user.
        If clean, then remove any allowed labels missing from existing entry.
        If labels or allowed_labels are not given, they are obtained
        from HTML form arguments, so an http request is then required.
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
            return set([l["value"] for l in self.get_docs("label", "value")])
        else:
            return set(self.current_user["labels"])


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
    "Publications list display page; by year or all."

    TEMPLATE = "publications.html"

    def get(self, year=None):
        subset = Subset(self.db)
        if year:
            subset.select_year(year)
        else:
            subset.select_all()
        self.render(self.TEMPLATE, publications=subset, year=year)


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
        result["publications_count"] = len(publications)
        full = utils.to_bool(self.get_argument("full", True))
        result["full"] = full
        result["publications"] = [self.get_publication_json(publ, full=full)
                                  for publ in publications]
        self.write(result)


class PublicationsFile(utils.DownloadParametersMixin, Publications):
    "Class adding methods for output of publications to a file."

    def get_filtered_publications(self):
        "Get the publications filtered according to form arguments."
        # Start with subset of publications based on given published years.
        years = self.get_arguments("years")
        if years:
            subset = functools.reduce(lambda s, t: s | t,
                                      [Subset(self.db, year=y) for y in years])
        # No given years: Start with all publications.
        else:
            subset = Subset(self.db, all=True)

        # If any labels, intersect with the union of those publications.
        labels = list(set(self.get_arguments("labels")))
        if labels:
            subset = subset & functools.reduce(lambda s, t: s | t,
                                               [Subset(self.db, label=l)
                                                for l in labels])

        # If any required labels, intersect with publications for each label.
        for label in set(self.get_arguments("labels_required")):
            subset = subset & Subset(self.db, label=label)

        # If any labels to exclude, remove those publications.
        for label in set(self.get_arguments("labels_excluded")):
            subset = subset - Subset(self.db, label=label)

        # Filter by active labels during a year (current, or explicit).
        active = self.get_argument("active", "")
        if settings["TEMPORAL_LABELS"] and active:
            s = Subset(self.db)
            s.select_active_labels(active)
            subset = subset & s

        return subset


class PublicationsCsv(PublicationsFile):
    "Publications CSV output."

    def get(self):
        "Show output selection page."
        all_labels = sorted([l["value"]
                             for l in self.get_docs("label", "value")])
        self.render("publications_csv.html",
                    year=self.get_argument("year", None),
                    labels=set(self.get_arguments("label")),
                    all_labels=all_labels,
                    cancel_url=self.get_argument("cancel_url", None))

    def post(self):
        writer = CsvWriter(self.db, self.application, **self.get_parameters())
        writer.write(self.get_filtered_publications())
        self.write(writer.get_content())
        self.set_header("Content-Type", constants.CSV_MIME)
        self.set_header("Content-Disposition", 
                        'attachment; filename="publications.csv"')


class PublicationsXlsx(PublicationsFile):
    "Publications XLSX output."

    def get(self):
        "Show output selection page."
        all_labels = sorted([l["value"]
                             for l in self.get_docs("label", "value")])
        self.render("publications_xlsx.html",
                    year=self.get_argument("year", None),
                    labels=set(self.get_arguments("label")),
                    all_labels=all_labels,
                    cancel_url=self.get_argument("cancel_url", None))
        
    # Authentication is *not* required!
    def post(self):
        "Produce XLSX output."
        writer = XlsxWriter(self.db, self.application, **self.get_parameters())
        writer.write(self.get_filtered_publications())
        self.write(writer.get_content())
        self.set_header("Content-Type", constants.XLSX_MIME)
        self.set_header("Content-Disposition", 
                        'attachment; filename="publications.xlsx"')


class PublicationsTxt(PublicationsFile):
    "Publications text file output."

    def get(self):
        "Show output selection page."
        all_labels = sorted([l["value"]
                             for l in self.get_docs("label", "value")])
        self.render("publications_txt.html",
                    year=self.get_argument("year", None),
                    labels=set(self.get_arguments("label")),
                    all_labels=all_labels,
                    cancel_url=self.get_argument("cancel_url", None))

    # Authentication is *not* required!
    def post(self):
        "Produce text output."
        writer = TextWriter(self.db, self.application, **self.get_parameters())
        writer.write(self.get_filtered_publications())
        self.write(writer.get_content())
        self.set_header("Content-Type", constants.TXT_MIME)
        self.set_header("Content-Disposition", 
                        'attachment; filename="publications.txt"')


class PublicationsNoPmid(PublicationMixin, RequestHandler):
    "Publications lacking PMID."

    def get(self):
        subset = Subset(self.db)
        subset.select_no_pmid()
        publications = subset.get_publications()
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
        subset = Subset(self.db)
        subset.select_no_doi()
        publications = subset.get_publications()
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
        subset = Subset(self.db)
        subset.select_no_label()
        self.render("publications_no_label.html", publications=subset)


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
        for publ1 in self.get_docs("publication", "modified"):
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
        limit = settings["LONG_PUBLICATIONS_LIST_LIMIT"]
        subset = Subset(self.db)
        subset.select_modified(limit=limit)
        publications = subset.get_publications()
        publications.sort(key=lambda p: p["modified"], reverse=True)
        self.render("publications_modified.html",
                    publications=publications,
                    limit=limit)


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


class PublicationFetch(PublicationMixin, RequestHandler):
    "Fetch publication(s) given list of DOIs or PMIDs."

    @tornado.web.authenticated
    def get(self):
        self.check_curator()
        fetched = self.get_cookie("fetched")
        self.clear_cookie("fetched")
        docs = []
        if fetched:
            for iuid in fetched.split("_"):
                try:
                    docs.append(self.db[iuid])
                except couchdb2.NotFoundError:
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
                publ = fetch_publication(self.db, identifier,
                                         override=override, labels=labels,
                                         clean=not self.is_admin(),
                                         rqh=self)
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
            self.set_error_flash(constants.REV_ERROR)
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
            self.set_error_flash(constants.REV_ERROR)
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
            self.set_error_flash(constants.REV_ERROR)
        except (tornado.web.MissingArgumentError, ValueError) as error:
            self.set_error_flash(str(error))
        if self.get_argument("__save__", "") == "continue":
            self.see_other("publication_xrefs", publication["_id"])
        else:
            self.see_other("publication", publication["_id"])


class PublicationBlacklist(PublicationMixin, RequestHandler):
    "Blacklist a specified publication."

    @tornado.web.authenticated
    def post(self, identifier):
        try:
            publication = self.get_publication(identifier)
            self.check_deletable(publication)
        except (KeyError, ValueError) as error:
            self.see_other("home", error=str(error))
            return
        blacklist = {constants.DOCTYPE: constants.BLACKLIST,
                     "_id": utils.get_iuid(),
                     "title": publication["title"],
                     "pmid": publication.get("pmid"),
                     "doi": publication.get("doi"),
                     "created": utils.timestamp(),
                     "owner": self.current_user["email"]}
        self.db.put(blacklist)
        self.delete_entity(publication)
        try:
            self.redirect(self.get_argument("next"))
        except tornado.web.MissingArgumentError:
            self.see_other("home")


class PublicationsBlacklisted(RequestHandler):
    "Display list of blacklisted publications, and remove entry from it."

    @tornado.web.authenticated
    def get(self):
        blacklisted = dict([(d["_id"], d) for d in 
                            self.get_docs("blacklist", "doi")])
        blacklisted.update(dict([(d["_id"], d) for d in 
                                 self.get_docs("blacklist", "pmid")]))
        self.render("publications_blacklisted.html", 
                    blacklisted=blacklisted.values())

    @tornado.web.authenticated
    def post(self):
        try:
            doc = self.db[self.get_argument("remove")]
        except KeyError:
            pass
        else:
            self.db.delete(doc)
        self.see_other("publications_blacklisted")


class ApiPublicationFetch(PublicationMixin, ApiMixin, RequestHandler):
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
            publ = fetch_publication(self.db, identifier,
                                     override=bool(data.get("override")),
                                     labels=data.get("labels", {}),
                                     rqh=self)
        except IOError as error:
            raise tornado.web.HTTPError(400, reason=str(error))
        except KeyError as error:
            raise tornado.web.HTTPError(409, reason=f"blacklisted {error}")
        self.write(
            dict(iuid=publ["_id"],
                 href=self.absolute_reverse_url("publication", publ["_id"])))


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


def fetch_publication(db, identifier, override=False,
                      labels={}, allowed_labels=None, clean=True,
                      rqh=None, account=None):
    """Fetch the publication given by identifier (PMID or DOI).
    If the publication is already in the database, the label,
    if given, is added. For a PMID, the publication is fetched from PubMed.
    For a DOI, an attempt is first made to get the publication from PubMed.
    If that does not work, Crossref is tried.
    Delay, timeout and API key for fetching is defined in the settings file.
    override: If True, overrides the blacklist.
    labels: Dictionary of labels (key: label, value: qualifier) to set.
            Only allowed labels for the curator are updated.
    clean: Remove any allowed labels missing from an existing entry.
    Raise IOError if no such publication found, or other error.
    Raise KeyError if publication is in the blacklist (and not override).
    """
    check_blacklisted(db, identifier, override=override)

    # Does the publication already exist in the database?
    try:
        current = utils.get_publication(db, identifier)
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
            raise IOError(f"{identifier} {str(error)}")

    else: # Not PMID: DOI identifier; search PubMed first.
        pmids = pubmed.search(doi=identifier,
                              timeout=settings["PUBMED_TIMEOUT"],
                              delay=settings["PUBMED_DELAY"],
                              api_key=settings["NCBI_API_KEY"])
        if len(pmids) == 1:  # Unique result: use it.
            try:
                new = pubmed.fetch(pmids[0],
                                   timeout=settings["PUBMED_TIMEOUT"],
                                   delay=settings["PUBMED_DELAY"],
                                   api_key=settings["NCBI_API_KEY"])
            except IOError:
                msg = f"No response from PubMed for {identifier}."
                if current:
                    msg += " Publication exists, but could not be updated."
                raise IOError(msg)
            except ValueError as error:
                raise IOError(f"{identifier} {str(error)}")
        else:  # No result, or ambiguous. Try Crossref.
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
                raise IOError(f"{identifier} {str(error)}")

    # Check blacklist registry again; other external id may be there.
    check_blacklisted(db, new.get("pmid"), override=override)
    check_blacklisted(db, new.get("doi"), override=override)

    # Find the current entry again by the other identifier.
    if current is None:
        # Maybe the publication has been fetched using the other identifier?
        if identifier_is_pmid:
            try:
                current = utils.get_publication(db, new.get("doi"))
            except KeyError:
                pass
        else:
            try:
                current = utils.get_publication(db, new.get("pmid"))
            except KeyError:
                pass

    # Update the current entry, if it exists.
    if current:
        with PublicationSaver(doc=current,
                              db=db, rqh=rqh, account=account) as saver:
            saver.update(new, updated_by_pmid=identifier_is_pmid)
            saver.fix_journal()
            saver.update_labels(labels=labels, clean=clean,
                                allowed_labels=allowed_labels)
        return current
    # Else create a new entry.
    else:
        with PublicationSaver(db=db, rqh=rqh, account=account) as saver:
            saver.update(new, updated_by_pmid=identifier_is_pmid)
            saver.fix_journal()
            saver.update_labels(labels=labels, allowed_labels=allowed_labels)
        return saver.doc

def check_blacklisted(db, identifier, override=False):
    """Raise KeyError if identifier blacklisted.
    If override, remove from blacklist.
    """
    blacklisted = utils.get_blacklisted(db, identifier)
    if blacklisted:
        if override:
            db.delete(blacklisted)
        else:
            raise KeyError(f"{identifier} is blacklisted.")
