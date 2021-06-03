"Researcher (person, but also possibly consortium or similar) pages."

import tornado.web

from . import constants
from . import publication
from . import settings
from . import utils
from .saver import Saver, SaverError
from .requesthandler import RequestHandler, ApiMixin


class ResearcherSaver(Saver):
    doctype = constants.RESEARCHER

    def set_family(self, value=None):
        "Set then family name from form data."
        assert self.rqh, "requires http request context"
        if value is None:
            value = utils.squish(self.rqh.get_argument("family", ""))
        if not value:
            raise ValueError("No family name provided.")
        self["family"] = value
        self["family_normalized"] = utils.to_ascii(value).lower()

    def set_given(self, value=None):
        "Set the given name from form data."
        assert self.rqh, "requires http request context"
        if value is None:
            value = utils.squish(self.rqh.get_argument("given", ""))
        self["given"] = value
        self["given_normalized"] = utils.to_ascii(value).lower()

    def set_initials(self, value=None):
        "Set the initials from form data."
        assert self.rqh, "requires http request context"
        if value is None:
            value = "".join(self.rqh.get_argument("initials", "").split())
        self["initials"] = value
        self["initials_normalized"] = utils.to_ascii(value).lower()

    def set_orcid(self, value=None):
        "Set ORCID from form data."
        assert self.rqh, "requires http request context"
        if value is None:
            value = self.rqh.get_argument("orcid", "").strip()
        if value:
            try:
                self.rqh.get_researcher(value)
            except KeyError:
                pass
            else:
                raise ValueError(f"Researcher entry exists for ORCID '{value}'")
        self["orcid"] = value or None

    def set_affiliations(self, affiliations=None):
        "Set affiliations from form data."
        assert self.rqh, "requires http request context"
        if affiliations is None:
            affiliations = [a.strip() for a in
                            self.rqh.get_argument("affiliations", "").split("\n")
                            if a.strip()]
        self["affiliations"] = affiliations

    def finalize(self):
        "Set the initials, in not done explicitly."
        super().finalize()
        if not self.get("initials"):
            value = "".join([n[0] for n in self.get("given", "").split() if n])
            self["initials"] = value
            self["initials_normalized"] = utils.to_ascii(value).lower()

    
class ResearcherMixin:
    "Mixin for access check methods."

    def is_editable(self, researcher):
        "Is the researcher editable by the current user?"
        return self.is_admin()

    def check_editable(self, researcher):
        "Raise ValueError if researcher is not editable."
        if self.is_editable(researcher): return
        raise ValueError("You may not edit the researcher.")

    def is_deletable(self, researcher):
        "Is the researcher deletable by the current user?"
        if not self.is_admin(): return False
        if self.get_count("publication/researcher", key=researcher["_id"]):
            return False
        return True

    def check_deletable(self, journal):
        "Raise ValueError if researcher is not deletable."
        if self.is_deletable(journal): return
        raise ValueError("You may not delete the researcher.")


class Researcher(ResearcherMixin, RequestHandler):
    "Researcher page with list of publications."

    def get(self, identifier):
        "Display the researcher."
        try:
            researcher = self.get_researcher(identifier)
        except KeyError as error:
            self.see_other("home", error=str(error))
            return
        publications = self.get_docs("publication/researcher",
                                     key=researcher["_id"])
        publications.sort(key=lambda i: i["published"], reverse=True)
        self.render("researcher.html",
                    researcher=researcher,
                    publications=publications,
                    is_editable=self.is_editable(researcher),
                    is_deletable=self.is_deletable(researcher))

    @tornado.web.authenticated
    def post(self, identifier):
        if self.get_argument("_http_method", None) == "delete":
            self.delete(identifier)
            return
        raise tornado.web.HTTPError(405, reason="POST only allowed for DELETE")

    @tornado.web.authenticated
    def delete(self, identifier):
        try:
            researcher = self.get_researcher(identifier)
            self.check_deletable(researcher)
        except (KeyError, ValueError) as error:
            self.see_other("home", error=str(error))
            return
        # Delete log entries
        for log in self.get_logs(researcher["_id"]):
            self.db.delete(log)
        self.db.delete(researcher)
        self.see_other("home")


class JsonMixin:
    "Get JSON for researcher."

    def get_json(self, researcher):
        URL = self.absolute_reverse_url
        result = dict()
        result["family"] = researcher["family"]
        result["given"] = researcher["given"]
        result["initials"] = researcher["initials"]
        result["orcid"] = researcher.get("orcid")
        result["affiliations"] = researcher["affiliations"]
        result["links"] = links = dict()
        links["self"] = {"href": URL("researcher_json", researcher["_id"])}
        links["display"] = {"href": URL("researcher", researcher["_id"])}
        try:
            result["n_publications"] = researcher["n_publications"]
        except KeyError:
            pass
        return result


class ResearcherJson(JsonMixin, Researcher):
    "Researcher JSON data."

    def get(self, identifier):
        "Display the researcher."
        try:
            researcher = self.get_researcher(identifier)
        except KeyError as error:
            raise tornado.web.HTTPError(404, reason="no such researcher")
        publications = self.get_docs("publication/researcher",
                                     key=researcher["_id"])
        publications.sort(key=lambda i: i["published"], reverse=True)
        result = dict()
        result["entity"] = "researcher"
        result["timestamp"] = utils.timestamp()
        result.update(self.get_json(researcher))
        result["publications"] = [self.get_publication_json(publ)
                                  for publ in publications]
        self.write(result)


class ResearcherAdd(ResearcherMixin, RequestHandler):
    "Researcher addition page."

    @tornado.web.authenticated
    def get(self):
        self.check_admin()
        self.render("researcher_add.html")

    @tornado.web.authenticated
    def post(self):
        self.check_admin()
        try:
            with ResearcherSaver(rqh=self) as saver:
                saver.set_family()
                saver.set_given()
                saver.set_initials()
                saver.set_orcid()
                saver.set_affiliations()
            researcher = saver.doc
        except ValueError as error:
            self.set_error_flash(str(error))
            self.see_other("researcher_add")
            return
        self.see_other("researcher", researcher["_id"])


class ResearcherEdit(ResearcherMixin, RequestHandler):
    "Researcher edit page."

    @tornado.web.authenticated
    def get(self, identifier):
        try:
            researcher = self.get_researcher(identifier)
            self.check_editable(researcher)
        except (KeyError, ValueError) as error:
            self.see_other("home", error=str(error))
            return
        self.render("researcher_edit.html", researcher=researcher)

    @tornado.web.authenticated
    def post(self, identifier):
        try:
            researcher = self.get_researcher(identifier)
            self.check_editable(researcher)
        except (KeyError, ValueError) as error:
            self.see_other("home", error=str(error))
            return
        try:
            with ResearcherSaver(doc=researcher, rqh=self) as saver:
                saver.check_revision()
                saver.set_family()
                saver.set_given()
                saver.set_initials()
                saver.set_orcid()
                saver.set_affiliations()
        except ValueError as error:
            self.set_error_flash(str(error))
        except SaverError:
            self.set_error_flash(utils.REV_ERROR)
        self.see_other("researcher", researcher["_id"])


class ResearcherPublicationsXlsx(publication.PublicationsXlsx):
    "Researcher publication XLSX output."

    def get(self, identifier):
        "Show output selection page."
        try:
            researcher = self.get_researcher(identifier)
        except KeyError as error:
            self.see_other("home", error=str(error))
            return
        self.render("researcher_publications_xlsx.html",
                    researcher=researcher)

    def post(self, identifier):
        try:
            self.researcher = self.get_researcher(identifier)
        except KeyError as error:
            self.see_other("home", error=str(error))
            return
        super().post()

    def get_filtered_publications(self):
        result = self.get_docs("publication/researcher",
                               key=self.researcher["_id"])
        result.sort(key=lambda i: i["published"], reverse=True)
        return result


class ResearcherPublicationsEdit(ResearcherMixin, RequestHandler):
    "Researcher publications edit page."

    @tornado.web.authenticated
    def get(self, identifier):
        try:
            researcher = self.get_researcher(identifier)
            self.check_editable(researcher)
        except (KeyError, ValueError) as error:
            self.see_other("home", error=str(error))
            return
        publications = self.get_publications(researcher)
        publications.sort(key=lambda p: p["published"], reverse=True)
        self.render("researcher_publications_edit.html",
                    researcher=researcher,
                    publications=publications)

    @tornado.web.authenticated
    def post(self, identifier):
        from publications.publication import PublicationSaver
        try:
            researcher = self.get_researcher(identifier)
            self.check_editable(researcher)
        except (KeyError, ValueError) as error:
            self.see_other("home", error=str(error))
            return
        publications = self.get_publications(researcher)
        add = self.get_arguments("add")
        try:
            for publication in publications:
                try:
                    if utils.to_bool(self.get_argument(publication["_id"])):
                        continue
                    with PublicationSaver(doc=publication, rqh=self) as saver:
                        for author in saver["authors"]:
                            if author.get("researcher") == researcher["_id"]:
                                author.pop("researcher")
                except tornado.web.MissingArgumentError:
                    if publication["_id"] not in add: continue
                    with PublicationSaver(doc=publication, rqh=self) as saver:
                        for author in saver["authors"]:
                            if author.get("researcher"): continue
                            if author["family_normalized"] != researcher["family_normalized"]: continue
                            length = min(len(author["initials_normalized"]),
                                         len(researcher["initials_normalized"]))
                            if author["initials_normalized"][:length] != researcher["initials_normalized"][:length]: continue
                            author["researcher"] = researcher["_id"]
                            break
        except ValueError as error:
            self.set_error_flash(str(error))
        except SaverError:
            self.set_error_flash(utils.REV_ERROR)
        self.see_other("researcher", researcher["_id"])

    def get_publications(self, researcher):
        "Get the publications for the researcher, including candidates."
        result = dict([(d["_id"], d)
                       for d in self.get_docs("publication/researcher",
                                              key=researcher["_id"])])
        name = f"{researcher['family_normalized']} {researcher['initials_normalized'][:1]}".strip()
        result.update(dict([(d["_id"], d)
                            for d in self.get_docs("publication/author",
                                                   key=name,
                                                   last=name+constants.CEILING)]))
        return list(result.values())


class Researchers(RequestHandler):
    "Researchers list page."

    def get(self):
        researchers = self.get_docs("researcher/name")
        for researcher in researchers:
            researcher["n_publications"] = \
                self.get_count("publication/researcher", key=researcher["_id"])
        self.render("researchers.html", researchers=researchers)


class ResearchersJson(JsonMixin, Researchers):
    "Researchers JSON list."

    def render(self, template, researchers):
        "Override; ignores template, and outpus JSON instead of HTML."
        URL = self.absolute_reverse_url
        result = dict()
        result["entity"] = "researchers"
        result["timestamp"] = utils.timestamp()
        result["links"] = links = dict()
        links["self"] = {"href": URL("researchers_json")}
        links["display"] = {"href": URL("researchers")}
        result["researchers"] = [self.get_json(r) for r in researchers]
        self.write(result)
