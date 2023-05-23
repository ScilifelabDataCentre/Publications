"Select a subset of publications."

import functools
import logging

import pyparsing as pp

from publications import constants
from publications import settings
from publications import utils
from publications.requesthandler import RequestHandler, DownloadParametersMixin

import publications.config
import publications.database
import publications.writer


class SubsetDisplay(DownloadParametersMixin, RequestHandler):
    "Display, edit and evaluate selection expressions."

    def get(self):
        "Display the initial subset definition page."
        self.render("subset.html", expression=None, publications=None)

    # Authentication is *not* required!
    def post(self):
        expression = self.get_argument("expression", "")
        try:
            if not expression:
                raise ValueError("No expression given.")
            subset = get_subset(self.db, expression)
        except ValueError as error:
            subset = Subset(self.db)  # Empty subset.
            message = str(error)
        else:
            message = None
        format = self.get_argument("format", "")
        if format and not message:
            parameters = self.get_parameters()
            if format == "CSV":
                writer = publications.writer.CsvWriter(self.db, self.application, **parameters)
                writer.write(subset)
                self.write(writer.get_content())
                self.set_header("Content-Type", constants.CSV_MIME)
                self.set_header(
                    "Content-Disposition", 'attachment; filename="publications.csv"'
                )
                return
            elif format == "XLSX":
                writer = publications.writer.XlsxWriter(self.db, self.application, **parameters)
                writer.write(subset)
                self.write(writer.get_content())
                self.set_header("Content-Type", constants.XLSX_MIME)
                self.set_header(
                    "Content-Disposition", 'attachment; filename="publications.xlsx"'
                )
                return
            elif format == "TXT":
                writer = publications.writer.TextWriter(self.db, self.application, **parameters)
                writer.write(subset)
                self.write(writer.get_content())
                self.set_header("Content-Type", constants.TXT_MIME)
                self.set_header(
                    "Content-Disposition", 'attachment; filename="publications.txt"'
                )
                return
            else:
                error = f"Unknown format '{format}"
        self.render(
            "subset.html", expression=expression, publications=subset, error=message
        )


class Subset:
    "Publication subset selection and operations."

    def __init__(
            self, db, all=False, recent=None, year=None, label=None, author=None, orcid=None, issn=None
    ):
        self.db = db
        self.iuids = set()
        if all:
            self.select_all()
        elif year:
            self.select_year(year)
        elif recent:
            self.select_recent(recent)
        elif label:
            self.select_label(label)
        elif author:
            self.select_author(author)
        elif orcid:
            self.select_orcid(orcid)
        elif issn:
            self.select_issn(issn)

    def __len__(self):
        return len(self.iuids)

    def __str__(self):
        return f"{len(self)} publications"

    def __repr__(self):
        return f"Subset({len(self)})"

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
            raise ValueError(f"'other' is not a Subset: {repr(other)}")
        if self.db is not other.db:
            raise ValueError("'other' is connected to a different database.")
        result = self.copy()
        result.iuids.update(other.iuids)
        return result

    def __and__(self, other):
        "Intersection of this subset and the other."
        if not isinstance(other, Subset):
            raise ValueError(f"'other' is not a Subset: {repr(other)}")
        if self.db is not other.db:
            raise ValueError("'other' is connected to a different database.")
        result = self.copy()
        result.iuids.intersection_update(other.iuids)
        return result

    def __sub__(self, other):
        "Difference of this subset and the other."
        if not isinstance(other, Subset):
            raise ValueError(f"'other' is not a Subset: {repr(other)}")
        if self.db is not other.db:
            raise ValueError("'other' is connected to a different database.")
        result = self.copy()
        result.iuids.difference_update(other.iuids)
        return result

    def __xor__(self, other):
        "Symmetric difference of this subset and the other."
        if not isinstance(other, Subset):
            raise ValueError(f"'other' is not a Subset: {repr(other)}")
        if self.db is not other.db:
            raise ValueError("'other' is connected to a different database.")
        result = self.copy()
        result.iuids.symmetric_difference_update(other.iuids)
        return result

    def get_publications(self):
        """Return the list of all selected publication documents.
        Sort by reverse order of (published, title), to make order stable.
        """
        publications = self.db.get_bulk(list(self.iuids))
        publications = [p for p in publications if p]
        publications.sort(key=lambda p: (p["published"], p["title"]), reverse=True)
        return publications

    def copy(self):
        "Return a copy if this subset."
        result = Subset(self.db)
        result.iuids.update(self.iuids)
        return result

    def select_all(self):
        "Select all publications."
        self._select("publication", "published")

    def select_recent(self, recent):
        "Select 'recent' number of publications."
        self._select("publication", "first_published", limit=recent, descending=True)

    def select_year(self, year):
        "Select the publications by the 'published' year."
        self._select("publication", "year", key=year)

    def select_label(self, label):
        """Select publications by the given label.
        If a wildcard '*' is present at the end, all suffixes are allowed
        from that point.
        """
        label = label.lower().strip()
        if label.endswith("*"):
            label = label[:-1]
            self._select(
                "publication", "label", key=label, last=label + constants.CEILING
            )
        else:
            self._select("publication", "label", key=label)

    def select_author(self, name):
        """Select publication by author name.
        The name must be of the form "Familyname Initials". It is normalized,
        i.e. non-ASCII characters are converted to most similar ASCII,
        and lower-cased. The match is exact, which is problematic;
        e.g. the initials used differs substantially between publications.
        If a wildcard '*' is present at the end, all suffixes are allowed
        from that point.
        """
        name = utils.to_ascii(name).lower().strip()
        if name.endswith("*"):
            name = name[:-1]
            self._select(
                "publication", "author", key=name, last=name + constants.CEILING
            )
        else:
            self._select("publication", "author", key=name)

    def select_orcid(self, orcid):
        "Select publications by researcher ORCID."
        try:
            researcher = publications.database.get_doc(self.db, "researcher", "orcid", orcid)
            iuid = researcher["_id"]
        except KeyError:
            iuid = "-"
        self._select("publication", "researcher", key=iuid)

    def select_issn(self, issn):
        "Select publications by the journal ISSN."
        self._select("publication", "issn", key=issn)

    def select_no_pmid(self):
        "Select all publications lacking PubMed identifier."
        self._select("publication", "no_pmid")

    def select_no_doi(self):
        "Select all publications lacking PubMed identifier."
        self._select("publication", "no_doi")

    def select_no_label(self):
        "Select all publications having no label"
        self._select("publication", "no_label")

    def select_published(self, date):
        """Select all publications 'published' after the given date, inclusive.
        This means the paper journal publication date.
        """
        self._select("publication", "published", key=date, last=constants.CEILING)

    def select_first_published(self, date):
        """Select all publications first published after the given date,
        inclusive. By 'first' is meant the first date of 'epublished'
        (online), and 'published' (paper journal date).
        """
        self._select("publication", "first_published", key=date, last=constants.CEILING)

    def select_epublished(self, date):
        """Select all publications by 'epublished' after the given date,
        inclusive.
        """
        self._select("publication", "epublished", key=date, last=constants.CEILING)

    def select_modified(self, date=None, limit=None):
        "Select all publications modified after the given date, inclusive."
        kwargs = {"descending": True, "limit": limit}
        if date is not None:
            kwargs["key"] = constants.CEILING
            kwargs["last"] = date
        self._select("publication", "modified", **kwargs)

    def select_active_labels(self, year):
        """Select all publications having a label active in the given year.
        If 'current' is given, then all currently active labels.
        If temporal labels are not configured, then produce an empty subset.
        """
        self.iuids = set()
        if not settings["TEMPORAL_LABELS"]:
            return
        if year.lower() == "current":
            labels = set([i.value for i in self.db.view("label", "current")])
        else:
            labels = set()
            for label in publications.database.get_docs(self.db, "label", "value"):
                started = label.get("started")
                if started and started <= year:  # Year as str
                    ended = label.get("ended")
                    if ended:
                        if year <= ended:  # Year as str
                            labels.add(label["value"])
                    else:  # Current
                        labels.add(label["value"])
        if labels:
            result = functools.reduce(
                lambda s, t: s | t, [Subset(self.db, label=l) for l in labels]
            )
            self.iuids = result.iuids

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


# Parser for the selection expression mini-language.


class _Function:
    "Abstract function; name and value for argument."

    def __init__(self, tokens):
        try:
            self.value = tokens[1]
        except IndexError:  # For argument-less functions.
            self.value = None

    def __repr__(self):
        return f"{self.__class__.__name__} ({self.value})"

    def evaluate(self, db, variables):
        raise NotImplementedError


class _Identifier(_Function):
    "Identifier for variable. Not really a function, but easiest this way."

    def __init__(self, tokens):
        self.value = tokens[0]

    def evaluate(self, db, variables):
        try:
            return variables[self.value]
        except KeyError as error:
            raise ValueError(f"No such variable '{self.value}'.")


class _Label(_Function):
    "Publications selected by label."

    def evaluate(self, db, variables):
        return Subset(db, label=self.value)


class _Year(_Function):
    "Publications selected by 'published' year."

    def evaluate(self, db, variables):
        return Subset(db, year=self.value)


class _Author(_Function):
    "Publications selected by author name, optionally with wildcard at end."

    def evaluate(self, db, variables):
        return Subset(db, author=self.value)


class _Orcid(_Function):
    "Publications selected by researcher ORCID."

    def evaluate(self, db, variables):
        return Subset(db, orcid=self.value)


class _Issn(_Function):
    "Publications selected by journal ISSN."

    def evaluate(self, db, variables):
        return Subset(db, issn=self.value)


class _Published(_Function):
    "Publications selected by 'published' after the given date, inclusive."

    def evaluate(self, db, variables):
        s = Subset(db)
        s.select_published(self.value)
        return s


class _First(_Function):
    """Publications selected by first publication date
    (the earliest of 'published' and 'epublished')
    after the given date, inclusive.
    """

    def evaluate(self, db, variables):
        s = Subset(db)
        s.select_first_published(self.value)
        return s


class _Online(_Function):
    "Publications selected by 'epublished' after the given date, inclusive."

    def evaluate(self, db, variables):
        s = Subset(db)
        s.select_epublished(self.value)
        return s


class _Modified(_Function):
    "Publications selected by modified after the given date, inclusive."

    def evaluate(self, db, variables):
        s = Subset(db)
        s.select_modified(date=self.value)
        return s


class _Active(_Function):
    "Publications having at least on label active in the given year."

    def evaluate(self, db, variables):
        s = Subset(db)
        s.select_active_labels(self.value or "current")
        return s


class _NoPmid(_Function):
    "Publications lacking PMID."

    def evaluate(self, db, variables):
        s = Subset(db)
        s.select_no_pmid()
        return s


class _NoDoi(_Function):
    "Publications lacking DOI."

    def evaluate(self, db, variables):
        s = Subset(db)
        s.select_no_doi()
        return s


class _NoLabel(_Function):
    "Publications lacking Label."

    def evaluate(self, db, variables):
        s = Subset(db)
        s.select_no_label()
        return s


class _Operator:
    "Subset operators."

    def __init__(self, tokens):
        self.operator = tokens[0]

    def __repr__(self):
        return self.operator


class _Union(_Operator):
    "Union of two subsets."

    def evaluate(self, s1, s2):
        return s1 | s2


class _Symdifference(_Operator):
    "Symmetric difference of two subsets."

    def evaluate(self, s1, s2):
        return s1 ^ s2


class _Intersection(_Operator):
    "Intersection of two subsets."

    def evaluate(self, s1, s2):
        return s1 & s2


class _Difference(_Operator):
    "Difference of two subsets."

    def evaluate(self, s1, s2):
        return s1 - s2


class _Expression:
    "Expression; one subset, or two subsets with an operator."

    def __init__(self, tokens):
        self.stack = list(tokens)

    def __repr__(self):
        items = []
        for s in self.stack:
            if isinstance(s, pp.ParseResults):
                items.append(repr(s[0]))
            else:
                items.append(repr(s))
        return f"Expression {', '.join(items)}"

    def evaluate(self, db, variables=None):
        "Evaluate the expression and return the resulting subset."
        self.stack.reverse()  # Left-to-right evaluation.
        if variables is None:
            variables = {}
        while len(self.stack) >= 3:
            s2 = self.stack.pop()
            op = self.stack.pop()
            s1 = self.stack.pop()
            if isinstance(s1, pp.ParseResults):
                s1 = s1[0].evaluate(db, variables=variables)
            elif isinstance(s1, _Function):
                s1 = s1.evaluate(db, variables)
            if isinstance(s2, pp.ParseResults):
                s2 = s2[0].evaluate(db, variables=variables)
            elif isinstance(s2, _Function):
                s2 = s2.evaluate(db, variables)
            self.stack.append(op.evaluate(s1, s2))
        if len(self.stack) != 1:
            raise ValueError(f"invalid stack {self.stack}")
        if isinstance(self.stack[0], _Function):
            return self.stack[0].evaluate(db, variables)
        elif isinstance(self.stack[0], pp.ParseResults):
            return self.stack[0][0].evaluate(db, variables=variables)
        else:
            return self.stack[0]


def get_subset(db, expression, variables=None):
    "Return the subset resulting from the selection expression evaluation."
    if not expression:
        return Subset(db)
    parser = get_parser()
    try:
        result = parser.parse_string(expression, parse_all=True)
    except pp.ParseException as error:
        raise ValueError(str(error))
    return result[0].evaluate(db, variables=variables)


def get_parser():
    "Construct and return the parser."

    left = pp.Suppress("(")
    right = pp.Suppress(")")
    value = pp.QuotedString(quote_char='"', esc_char="\\") | pp.CharsNotIn(")")
    identifier = pp.Word(pp.alphas, pp.alphanums).set_parse_action(_Identifier)

    label = (pp.Keyword("label") + left + value + right).set_parse_action(_Label)
    year = (pp.Keyword("year") + left + value + right).set_parse_action(_Year)
    author = (pp.Keyword("author") + left + value + right).set_parse_action(_Author)
    orcid = (pp.Keyword("orcid") + left + value + right).set_parse_action(_Orcid)
    issn = (pp.Keyword("issn") + left + value + right).set_parse_action(_Issn)
    published = (pp.Keyword("published") + left + value + right).set_parse_action(
        _Published
    )
    first = (pp.Keyword("first") + left + value + right).set_parse_action(_First)
    online = (pp.Keyword("online") + left + value + right).set_parse_action(_Online)
    modified = (pp.Keyword("modified") + left + value + right).set_parse_action(
        _Modified
    )
    no_pmid = (pp.Keyword("no_pmid") + left + right).set_parse_action(_NoPmid)
    no_doi = (pp.Keyword("no_doi") + left + right).set_parse_action(_NoDoi)
    no_label = (pp.Keyword("no_label") + left + right).set_parse_action(_NoLabel)
    function = (
        label
        | year
        | author
        | orcid
        | issn
        | published
        | first
        | online
        | modified
        | no_pmid
        | no_doi
        | no_label
    )

    if settings["TEMPORAL_LABELS"]:
        current = (pp.Keyword("active") + left + right).set_parse_action(_Active)
        active = (pp.Keyword("active") + left + value + right).set_parse_action(_Active)
        function = function | current | active

    union = pp.Literal("+").set_parse_action(_Union)
    symdifference = pp.Literal("^").set_parse_action(_Symdifference)
    intersection = pp.Literal("#").set_parse_action(_Intersection)
    difference = pp.Literal("-").set_parse_action(_Difference)
    operator = union | symdifference | difference | intersection

    expression = pp.Forward()
    atom = function | identifier | pp.Group(left + expression + right)
    expression <<= atom + (operator + atom)[...]
    expression.set_parse_action(_Expression)
    expression.ignore("!" + pp.rest_of_line)
    return expression


if __name__ == "__main__":
    logging.getLogger("publications").disabled = True
    publications.config.load_settings_from_file()
    db = publications.database.get_db()

    parser = get_parser()

    variables = dict(blah=Subset(db, year="2010"))

    line = """((label(Clinical Genomics Linköping) +
 label(Clinical Genomics Gothenburg)) +
 label(Clinical Genomics Lund) +
 label(Clinical Genomics Uppsala) +
 label(Clinical Genomics Stockholm) +
 label(Clinical Genomics Umeå) + 
 label(Clinical Genomics Örebro)) #
 (year(2020) + year(2019) +year(2018) + year(2017)) + blah"""
    print(">>>", get_subset(db, line, variables=variables))

    print("===", get_subset(db, "year(2020)"))

    labels = []
    for name in [
        "Clinical Genomics Linköping",
        "Clinical Genomics Gothenburg",
        "Clinical Genomics Lund",
        "Clinical Genomics Uppsala",
        "Clinical Genomics Stockholm",
        "Clinical Genomics Umeå",
        "Clinical Genomics Örebro",
    ]:
        labels.append(Subset(db, label=name))
        print(name, ":", labels[-1])
    labels = functools.reduce(lambda s, t: s | t, labels)
    print("labels :", labels)
    years = []
    for year in ["2017", "2018", "2019", "2020"]:
        years.append(Subset(db, year=year))
        print(year, ":", years[-1])
    years = functools.reduce(lambda s, t: s | t, years)
    print("years :", years)
    print("labels # years :", labels & years)

    print()

    s1 = Subset(db, label="National Genomics Infrastructure")
    print(s1)
    s2 = Subset(db, year="2020")
    print(s2)
    s3 = Subset(db, label="Spatial proteomics")
    print(s3)
    print("s1-s2-s3 =", s1 - s2 - s3)
    print("(s1-s2)-s3 =", (s1 - s2) - s3)
    print("s1-(s2-s3) =", s1 - (s2 - s3))
