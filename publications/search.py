"Search for terms in publications."

import logging

from publications import constants
from publications import settings
from publications import utils
from publications.requesthandler import RequestHandler


SEARCH_REMOVE = set(constants.SEARCH_REMOVE)
SEARCH_IGNORE = set(constants.SEARCH_IGNORE)


class Search(RequestHandler):
    """Search publications for terms in fields of publication docs:
    author, title, notes, pmid, doi, published, epublished, issn, journal,
    label_parts.
    """

    def get(self):
        terms = self.get_argument("terms", "")
        # The search term is quoted; consider a single phrase.
        if terms.startswith('"') and terms.endswith('"'):
            terms = [terms[1:-1]]
        # Split up into separate terms.
        else:
            # Remove DOI and PMID prefixes and lowercase.
            terms = [
                utils.strip_prefix(t) for t in self.get_argument("terms", "").split()
            ]

        iuids = set()

        # If a term is an ORCID, find researcher and her publications.
        # This must be done before the terms are lower-cased.
        researchers = set()
        for term in terms:
            view = self.db.view("researcher", "orcid", key=term)
            researchers.update([r.id for r in view])
        iuids.update(self.search("publication/researcher", researchers))

        # For subsequent searches, lower-case all terms.
        terms = [t.lower() for t in terms if t]

        # Keep all characters for these searches.
        for viewname in [
            None,
            "publication/author",
            "publication/doi",
            "publication/published",
            "publication/epublished",
            "publication/issn",
            "publication/journal",
            "publication/xref",
        ]:
            iuids.update(self.search(viewname, terms))

        # Remove set of insignificant characters for these seaches.
        terms = ["".join([c for c in t if c not in SEARCH_REMOVE]) for t in terms]
        terms = [t for t in terms if t]
        for viewname in [
            "publication/title",
            "publication/notes",
            "publication/pmid",
            "publication/label_parts",
        ]:
            iuids.update(self.search(viewname, terms))

        # Finally get the publication documents for IUIDs
        publications = [self.get_publication(iuid) for iuid in iuids]
        publications.sort(key=lambda p: p["published"], reverse=True)
        self.render(
            "search.html",
            publications=publications,
            terms=self.get_argument("terms", ""),
        )

    def search(self, designview, terms):
        "Search the given view using the terms. Return set of IUIDs."
        result = set()
        if designview is None:
            # IUID of publication entry; check that it really is a publication.
            for term in terms:
                try:
                    result.add(self.get_publication(term)["_id"])
                except KeyError:
                    pass
        else:
            designname, viewname = designview.split("/")
            for term in terms:
                if term in SEARCH_IGNORE:
                    continue
                view = self.db.view(
                    designname,
                    viewname,
                    startkey=term,
                    endkey=term + constants.CEILING,
                    reduce=False,
                )
                for item in view:
                    result.add(item.id)
        return result


class SearchJson(Search):
    "Output search results in JSON."

    def render(self, template, **kwargs):
        URL = self.absolute_reverse_url
        publications = kwargs["publications"]
        terms = kwargs["terms"]
        result = dict()
        result["entity"] = "publications search"
        result["timestamp"] = utils.timestamp()
        result["terms"] = terms
        result["links"] = links = dict()
        links["self"] = {"href": URL("search_json", terms=terms)}
        links["display"] = {"href": URL("search", terms=terms)}
        result["publications_count"] = len(publications)
        result["publications"] = [
            self.get_publication_json(publication) for publication in publications
        ]
        self.write(result)
