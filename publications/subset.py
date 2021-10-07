"Select a subset of publications."

from publications import settings
from publications import utils


class Subset:
    "Select a subset of publications."

    def __init__(self, db, all=False, year=None, label=None):
        self.db = db
        self.selected = {}
        if all:
            self.select_all()
        elif year:
            self.select_year(year)
        elif label:
            self.select_label(label)

    def __len__(self):
        return len(self.selected)

    def __str__(self):
        return f"{len(self)} publications"

    def __contains__(self, iuid):
        return iuid in self.selected

    def __iter__(self):
        """Return an iterator over all selected publication documents,
        sorted by reverse 'published' order.
        """
        return iter(sorted(self.selected.values(), 
                           key=lambda p: p['published'],
                           reverse=True))

    def __add__(self, other):
        "Union of this subset and the other."
        if not isinstance(other, Subset):
            raise ValueError("'other' is not a Subset")
        if self.db is not other.db:
            raise ValueError("'other' is connected to a different database.")
        result = self.copy()
        result.selected.update(other.selected)
        return result

    def __sub__(self, other):
        "Difference of this subset and the other."
        if not isinstance(other, Subset):
            raise ValueError("'other' is not a Subset")
        if self.db is not other.db:
            raise ValueError("'other' is connected to a different database.")
        result = self.copy()
        for iuid in other.selected:
            result.selected.pop(iuid, None)
        return result

    def __truediv__(self, other):
        "Intersection of this subset and the other."
        if not isinstance(other, Subset):
            raise ValueError("'other' is not a Subset")
        if self.db is not other.db:
            raise ValueError("'other' is connected to a different database.")
        result = self.copy()
        for iuid in set(result.selected.keys()).difference(other.selected.keys()):
            result.selected.pop(iuid)
        return result

    def copy(self):
        "Return a copy if this subset."
        result = Subset(self.db)
        result.selected.update(self.selected)
        return result

    def select_all(self):
        "Select all publications."
        self._select("publication", "published",
                         key="", last=constants.CEILING)

    def select_year(self, year):
        "Select the publications by the 'published' year."
        self._select("publication", "year", key=year)

    def select_label(self, label, union=True):
        "Select the publication by the given label."
        self._select("publication", "label", key=label.lower())

    def _select(self, designname, viewname, key=None, last=None):
        "Select the documents by design, view and key."
        kwargs = {}
        if key is None:
            pass
        elif last is None:
            kwargs["key"] = key
        else:
            kwargs["startkey"] = key
            kwargs["endkey"] = last
        view = self.db.view(designname,
                            viewname,
                            include_docs=True,
                            reduce=False,
                            **kwargs)
        self.selected = dict([(i.id, i.doc) for i in view])


if __name__ == "__main__":
    utils.load_settings()
    db = utils.get_db()
    s = Subset(db)
    print("0d3c758a29a144ae98a4c7540982c2fc" in s)
    s1 = Subset(db, year="2021")
    print(s1)
    print("0d3c758a29a144ae98a4c7540982c2fc" in s1)
    s2 = Subset(db, label="Affinity Proteomics Uppsala")
    print(s2)
    print(s1+s2)
    print(s1-s2)
    print(s1/s2)
