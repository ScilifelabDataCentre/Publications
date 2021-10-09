"Select a subset of publications."

from publications import constants
from publications import settings
from publications import utils


class Subset:
    "Publication subset selection and operations."

    def __init__(self, db, all=False, year=None, label=None,
                 orcid=None, author=None, issn=None):
        self.db = db
        self.iuids = set()
        if all:
            self.select_all()
        elif year:
            self.select_year(year)
        elif label:
            self.select_label(label)
        elif orcid:
            self.select_orcid(orcid)
        elif author:
            self.select_author(author)
        elif issn:
            self.select_issn(issn)

    def __len__(self):
        return len(self.iuids)

    def __str__(self):
        return f"{len(self)} publications"

    def __contains__(self, iuid):
        return iuid in self.iuids

    def __iter__(self):
        """Return an iterator over all selected publication documents,
        sorted by reverse 'published' order.
        """
        return iter(self.get_publications())

    def __or__(self, other):
        "Union of this subset and the other."
        if not isinstance(other, Subset):
            raise ValueError("'other' is not a Subset")
        if self.db is not other.db:
            raise ValueError("'other' is connected to a different database.")
        result = self.copy()
        result.iuids.update(other.iuids)
        return result

    def __and__(self, other):
        "Intersection of this subset and the other."
        if not isinstance(other, Subset):
            raise ValueError("'other' is not a Subset")
        if self.db is not other.db:
            raise ValueError("'other' is connected to a different database.")
        result = self.copy()
        result.iuids.intersection_update(other.iuids)
        return result

    def __sub__(self, other):
        "Difference of this subset and the other."
        if not isinstance(other, Subset):
            raise ValueError("'other' is not a Subset")
        if self.db is not other.db:
            raise ValueError("'other' is connected to a different database.")
        result = self.copy()
        result.iuids.difference_update(other.iuids)
        return result

    def get_publications(self, order="published"):
        """Return the list of all selected publication documents.
        Sort by reverse order of the given field, if given.
        """
        publications = self.db.get_bulk(list(self.iuids))
        publications = [p for p in publications if p]
        if order:
            publications.sort(key=lambda p: p[order], reverse=True)
        return publications

    def copy(self):
        "Return a copy if this subset."
        result = Subset(self.db)
        result.iuids.update(self.iuids)
        return result

    def select_all(self, limit=None):
        "Select all publications. Sort by reverse order of the published date."
        self._select("publication", "published",
                     key=constants.CEILING, last="",
                     descending=True, limit=limit)

    def select_year(self, year, limit=None):
        "Select the publications by the 'published' year."
        self._select("publication", "year", key=year, limit=limit)

    def select_label(self, label, limit=None):
        "Select publications by the given label."
        self._select("publication", "label", key=label.lower(), limit=limit)

    def select_issn(self, issn, limit=None):
        "Select publications by the journal ISSN."
        self._select("publication", "issn", key=issn, limit=limit)

    def select_author(self, name, limit=None):
        """Select publication by author name.
        The name must be of the form "Familyname Initials". It is normalized, i.e.
        non-ASCII characters are converted to most similar ASCII, and lower-cased.
        The match is exact, which is problematic; e.g. the initials used differs
        substantially between publications.
        If a wildcard '*' is added at the end, all suffixes are allow from that point.
        """
        name = utils.to_ascii(name).lower()
        if "*" in name:
            name = name[:-1]
            self._select("publication", "author", key=name, last=name+constants.CEILING)
        else:
            self._select("publication", "author", key=name)

    def select_researcher(self, orcid, limit=None):
        "Select publications by researcher ORCID."
        try:
            researcher = utils.get_doc(self.db, "researcher", "orcid", orcid)
            iuid = researcher["_id"]
        except KeyError:
            iuid = "-"
        self._select("publication", "researcher", key=iuid)

    def select_no_pmid(self, limit=None):
        "Select all publications lacking PubMed identifier."
        self._select("publication", "no_pmid", limit=limit)

    def select_no_doi(self, limit=None):
        "Select all publications lacking PubMed identifier."
        self._select("publication", "no_doi", limit=limit)

    def select_no_label(self, limit=None):
        "Select all publications having no label"
        self._select("publication", "no_label", limit=limit)

    def select_recently_published(self, date, limit=None):
        "Select all publications published after the given date, inclusive."
        self._select("publication", "published",
                     key=date, last=constants.CEILING, limit=limit)

    def select_recently_modified(self, date=None, limit=10):
        "Select all publications modified after the given date, inclusive."
        kwargs = {"descending": True}
        if date is not None:
            kwargs["key"] = constants.CEILING
            kwargs["last"] = date
        self._select("publication", "modified", limit=limit, **kwargs)

    def _select(self, designname, viewname, key=None, last=None, **kwargs):
        "Select the documents by design, view and key."
        kwargs["reduce"] = False
        if key is None:
            pass
        elif last is None:
            kwargs["key"] = key
        else:
            kwargs["startkey"] = key
            kwargs["endkey"] = last
        view = self.db.view(designname, viewname, **kwargs)
        self.iuids = set([i.id for i in view])


if __name__ == "__main__":
    utils.load_settings()
    db = utils.get_db()
    s1 = Subset(db)
    s1.select_issn("1469-8137")
    print(s1)
    s2 = Subset(db)
    s2.select_issn("0028-646X")
    print(s2)
    print(s1 & s2)

    
