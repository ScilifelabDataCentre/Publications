"Select a subset of publications."

import logging

import pyparsing as pp

from publications import constants
from publications import settings
from publications import utils
from publications.requesthandler import RequestHandler


class SubsetDisplay(RequestHandler):
    "Display, edit and evaluate selection expressions."

    def get(self):
        "Display the initial subset definition page."
        self.render("subset.html", expression=None, publications=None)

    # Authentication is *not* required!
    def post(self):
        expression = self.get_argument("expression")
        try:
            subset = get_subset(self.db, expression)
        except ValueError as error:
            self.set_error_flash(error)
        self.render("subset.html", expression=expression, publications=subset)


class Subset:
    "Publication subset selection and operations."

    def __init__(self, db, all=False, year=None, label=None,
                 author=None, orcid=None, issn=None):
        self.db = db
        self.iuids = set()
        if all:
            self.select_all()
        elif year:
            self.select_year(year)
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

    def __xor__(self, other):
        "Symmetric difference of this subset and the other."
        if not isinstance(other, Subset):
            raise ValueError("'other' is not a Subset")
        if self.db is not other.db:
            raise ValueError("'other' is connected to a different database.")
        result = self.copy()
        result.iuids.symmetric_difference_update(other.iuids)
        return result

    def get_publications(self, order="published"):
        """Return the list of all selected publication documents.
        Sort by reverse order of the given field, if given.
        """
        publications = self.db.get_bulk(list(self.iuids))
        publications = [p for p in publications if p]
        if order:
            publications.sort(key=lambda p: p.get(order, ''), reverse=True)
        return publications

    def copy(self):
        "Return a copy if this subset."
        result = Subset(self.db)
        result.iuids.update(self.iuids)
        return result

    def select_all(self):
        "Select all publications. Sort by reverse order of the published date."
        self._select("publication", "published",
                     key=constants.CEILING, 
                     last="",
                     descending=True)

    def select_year(self, year):
        "Select the publications by the 'published' year."
        self._select("publication", "year", key=year)

    def select_label(self, label):
        "Select publications by the given label."
        self._select("publication", "label", key=label.lower())

    def select_author(self, name):
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

    def select_orcid(self, orcid):
        "Select publications by researcher ORCID."
        try:
            researcher = utils.get_doc(self.db, "researcher", "orcid", orcid)
            iuid = researcher["_id"]
        except KeyError:
            iuid = "-"
        self._select("publication", "researcher", key=iuid)

    def select_issn(self, issn:
        "Select publications by the journal ISSN."
        self._select("publication", "issn", key=issn)

    def select_no_pmid(self):
        "Select all publications lacking PubMed identifier."
        self._select("publication", "no_pmid")

    def select_no_doi(self):
        "Select all publications lacking PubMed identifier."
        self._select("publication", "no_doi")

    def select_no_published(self):
        "Select all publications lacking 'published' field."
        self._select("publication", "no_published")

    def select_no_label(self):
        "Select all publications having no label"
        self._select("publication", "no_label")

    def select_published(self, date):
        "Select all publications published after the given date, inclusive."
        self._select("publication", "published",
                     key=date, last=constants.CEILING)

    def select_modified(self, date=None, limit=10):
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


# Parser for the selection expression mini-language.

class _Identifier:
    "Identifier for variable."

    def __init__(self, tokens):
        self.identifier = tokens[0]

    def evaluate(self, db, variables, stack):
        stack.append(variables[self.identifier])


class _Function:
    "Function; name and value for argument."

    def __init__(self, tokens):
        try:
            self.value = tokens[1]
        except IndexError:      # For argument-less functions.
            pass

class _Label(_Function):
    "Publications selected by label."

    def evaluate(self, db, variables, stack):
        stack.append(Subset(db, label=self.value))


class _Year(_Function):
    "Publications selected by 'published' year."

    def evaluate(self, db, variables, stack):
        stack.append(Subset(db, year=self.value))

class _Author(_Function):
    "Publications selected by author name, optionally with wildcard at end."

    def evaluate(self, db, variables, stack):
        stack.append(Subset(db, author=self.value))


class _Orcid(_Function):
    "Publications selected by researcher ORCID."

    def evaluate(self, db, variables, stack):
        stack.append(Subset(db, orcid=self.value))


class _Issn(_Function):
    "Publications selected by journal ISSN."

    def evaluate(self, db, variables, stack):
        stack.append(Subset(db, issn=self.value))


class _Published(_Function):
    "Publications selected by published after the given date, inclusive."

    def evaluate(self, db, variables, stack):
        s = Subset(db)
        s.select_published(self.value)
        stack.append(s)


class _Modified(_Function):
    "Publications selected by modified after the given date, inclusive."

    def evaluate(self, db, variables, stack):
        s = Subset(db)
        s.select_modified(self.value)
        stack.append(s)


class _NoPmid(_Function):
    "Publications lacking PMID."

    def evaluate(self, db, variables, stack):
        s = Subset(db)
        s.select_no_pmid()
        stack.append(s)


class _NoDoi(_Function):
    "Publications lacking DOI."

    def evaluate(self, db, variables, stack):
        s = Subset(db)
        s.select_no_doi()
        stack.append(s)


class _NoLabel(_Function):
    "Publications lacking Label."

    def evaluate(self, db, variables, stack):
        s = Subset(db)
        s.select_no_label()
        stack.append(s)


class _Operation:
    "Subset operators."

    def __init__(self, tokens):
        self.operator = tokens[0]

    def evaluate(self, db, variables, stack):
        stack.append(self.operator)


class _Expression:
    "Expression; one subset, or two subsets with an operation."

    def __init__(self, tokens):
        self.tokens = tokens

    def get_subset(self, db, variables=None):
        stack = []
        self.evaluate(db, variables=variables, stack=stack)
        while len(stack) >= 3:
            self.reduce(stack)
        if len(stack) != 1:
            raise ValueError(f"invalid stack {stack}")
        return stack[0]

    def evaluate(self, db, variables=None, stack=None):
        "Evaluate the expression."
        if variables is None:
            variables = {}
        if stack is None:
            self.stack = []
        for token in self.tokens:
            if isinstance(token, pp.ParseResults):
                token[0].evaluate(db, variables, stack)
            else:
                token.evaluate(db, variables, stack)
        self.reduce(stack)

    def reduce(self, stack):
        if len(stack) >= 3:
            s2 = stack.pop()
            op = stack.pop()
            s1 = stack.pop()
            if op == "+":
                stack.append(s1 | s2)
            elif op == "^":
                stack.append(s1 ^ s2)
            elif op == "-":
                stack.append(s1 - s2)
            elif op == "#":
                stack.append(s1 & s2)


def get_subset(db, expression, variables=None):
    "Return the subset resulting from the selection expression evaluation."
    if not expression:
        return Subset(db)
    parser = get_parser()
    try:
        result = parser.parseString(expression, parseAll=True)
    except pp.ParseException as error:
        raise ValueError(str(error))
    return result[0].get_subset(db, variables=variables)

def get_parser():
    "Construct and return the parser."

    left = pp.Suppress("(")
    right = pp.Suppress(")")
    value = pp.CharsNotIn(")")
    identifier = pp.Word(pp.alphas, pp.alphanums).setParseAction(_Identifier)

    label = (pp.Keyword("label") + left+value+right).setParseAction(_Label)
    year = (pp.Keyword("year") + left+value+right).setParseAction(_Year)
    author = (pp.Keyword("author") + left+value+right).setParseAction(_Author)
    orcid = (pp.Keyword("orcid") + left+value+right).setParseAction(_Orcid)
    issn = (pp.Keyword("issn") + left+value+right).setParseAction(_Issn)
    published = (pp.Keyword("published") + left+value+right).setParseAction(_Published)
    modified = (pp.Keyword("modified") + left+value+right).setParseAction(_Modified)
    no_pmid = (pp.Keyword("no_pmid") + left+right).setParseAction(_NoPmid)
    no_doi = (pp.Keyword("no_doi") + left+right).setParseAction(_NoDoi)
    no_label = (pp.Keyword("no_label") + left+right).setParseAction(_NoLabel)
    functions = (label | year| author | orcid | issn | published | modified |
                 no_pmid | no_doi | no_label)

    union = pp.Literal("+").setParseAction(_Operation)
    symdifference = pp.Literal("^").setParseAction(_Operation)
    intersection = pp.Literal("#").setParseAction(_Operation)
    difference = pp.Literal("-").setParseAction(_Operation)
    ops = union | symdifference | difference | intersection

    expr = pp.Forward()
    atom = (ops[...] + (functions | identifier | pp.Group(left + expr + right)))
    term = pp.Forward()
    term = atom + (ops + term)[...]
    expr <<= term + (ops + term)[...]
    expr.setParseAction(_Expression)
    expr.ignore("!" + pp.restOfLine)
    return expr


if __name__ == "__main__":
    logging.getLogger().disabled = True
    utils.load_settings()
    db = utils.get_db()

    subset = Subset(db)
    subset.select_no_published()
    print(subset)
    print(subset.iuids)

    # parser = get_parser()
    # y2020 = Subset(db, year="2020")
    # variables = dict(y2020=y2020)

    # # Published during January 2020 with NGI.
    # line = "(published(2020-01-01) - published(2020-02-01)) # label(National Genomics Infrastructure)"
    # print(line)
    # print("===", get_subset(db, line, variables=variables))
    # s1 = Subset(db)
    # s1.select_published("2020-01-01")
    # s2 = Subset(db)
    # s2.select_published("2020-02-01")
    # print("---", (s1-s2) & Subset(db, label="National Genomics Infrastructure"))
    # print()

    # line ="(year(2010) # label(National Genomics Infrastructure)) # author(a*)"
    # print("===", get_subset(db, line, variables=variables))
