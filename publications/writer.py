"Write a set of publications to a file."

import csv
import io

import xlsxwriter

from publications import constants
from publications import settings
from publications import utils


class Writer:
    "Abstract writer of publications to a file."

    _QUOTING = dict(all=csv.QUOTE_ALL,
                    minimal=csv.QUOTE_MINIMAL,
                    nonnumeric=csv.QUOTE_NONNUMERIC,
                    none=csv.QUOTE_NONE)

    def __init__(self, db, app, **kwargs):
        self.db = db
        self.app = app
        self.parameters = {"all_authors": False,
                           "issn": False,
                           "single_label": False,
                           "delimiter": ",",
                           "quoting": "nonnumeric",
                           "encoding": "utf-8",
                           "numbered": False,
                           "maxline": None,
                           "doi_url": False,
                           "pmid_url": False}
        self.parameters.update(kwargs)
        self.parameters["quoting"] = \
            self._QUOTING.get(self.parameters["quoting"].lower(),
                              csv.QUOTE_NONNUMERIC)

    def absolute_reverse_url(self, name, *args, **query):
        if name is None:
            path = ""
        else:
            path = self.app.reverse_url(name, *args, **query)
        return settings["BASE_URL"].rstrip("/") + path

    def write(self, publications):
        "Write the set of publications given the parameters."
        raise NotImplementedError

    def get_content(self):
        "Get the file contents as bytes."
        raise NotImplementedError


class TabularWriter(Writer):
    "Abstract writer of publications to a tabular file."

    def write(self, publications):
        "Write the set of publications given the parameters."
        row = ["Title",
               "Authors",
               "Journal"]
        if self.parameters['issn']:
            self.issn_l_map = dict([(r.value, r.key) for r in 
                                    self.db.view("journal", "issn_l")])
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
            ])
        self.write_header(row)
        complete = self.parameters['all_authors']
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
                                            complete=complete),
                journal.get("title")]
            if self.parameters['issn']:
                row.append(journal.get("issn"))
                row.append(self.issn_l_map.get(journal.get("issn")))
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
                ]
            )
            # Labels to output: single per row, or concatenated.
            labels = sorted(list(publication.get("labels", {}).items()))
            if self.parameters["single_label"]:
                for label, qualifier in labels:
                    row[label_pos] = label
                    row[label_pos+1] = qualifier
                    self.write_row(row)
            else:
                row[label_pos] = "|".join([l[0] for l in labels])
                row[label_pos+1] = "|".join([l[1] or "" for l in labels])
                self.write_row(row)

    def write_header(self, row):
        "Write the header row."
        raise NotImplementedError

    def write_row(self, row):
        "Write a row of values."
        raise NotImplementedError


class CsvWriter(TabularWriter):
    "Write publications to a CSV file."

    def __init__(self, db, app, **kwargs):
        super().__init__(db, app, **kwargs)
        self.csvbuffer = io.StringIO()
        if self.parameters["delimiter"].lower() == "comma":
            delimiter = ","
        elif self.parameters["delimiter"].lower() == "semi-colon":
            delimiter = ";"
        elif self.parameters["delimiter"].lower() == "tab":
            delimiter = "\t"
        else:
            delimiter = self.parameters["delimiter"]
        self.writer = csv.writer(self.csvbuffer,
                                 delimiter=delimiter,
                                 quoting=self.parameters["quoting"])

    def write_header(self, row):
        self.write_row(row)

    def write_row(self, row):
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

    def get_content(self):
        content = self.csvbuffer.getvalue()
        return content.encode(self.parameters["encoding"], "backslashreplace")


class XlsxWriter(TabularWriter):
    "Write publications to an XLSX (Excel) file."

    def __init__(self, db, app, **kwargs):
        super().__init__(db, app, **kwargs)
        self.xlsxbuffer = io.BytesIO()
        self.workbook = xlsxwriter.Workbook(self.xlsxbuffer,
                                            {"in_memory": True})
        self.ws = self.workbook.add_worksheet("Publications")

    def write_header(self, row):
        "Write the header row."
        self.ws.freeze_panes(1, 0)
        self.ws.set_row(0, None, self.workbook.add_format({"bold": True}))
        self.ws.set_column(0, 1, 40) # Title
        self.ws.set_column(2, 2, 20) # Authors
        self.ws.set_column(3, 3, 10) # Journal
        if self.parameters['issn']:
            self.ws.set_column(11, 11, 30) # DOI
            self.ws.set_column(12, 12, 10) # PMID
            self.ws.set_column(13, 13, 30) # Labels
            self.ws.set_column(14, 15, 20) # Qualifiers and IUID
        else:
            self.ws.set_column(9, 9, 30) # DOI
            self.ws.set_column(10, 10, 10) # PMID
            self.ws.set_column(11, 11, 30) # Labels
            self.ws.set_column(12, 13, 20) # Qualifiers and IUID
        self.x = 0
        self.write_row(row)

    def write_row(self, row):
        "Write a row of values."
        for y, item in enumerate(row):
            if isinstance(item, str): # Remove CR characters; keep newline.
                self.ws.write(self.x, y, item.replace("\r", ""))
            else:
                self.ws.write(self.x, y, item)
        self.x += 1

    def get_content(self):
        "Get the file contents as bytes."
        self.workbook.close()
        self.xlsxbuffer.seek(0)
        return self.xlsxbuffer.getvalue()


class TextWriter(Writer):
    "Write publications to a text file."

    def write(self, publications):
        "Write the set of publications given the parameters."
        self.text = io.StringIO()
        for number, publication in enumerate(publications, 1):
            if self.parameters['numbered']:
                self.line = f"{number}."
                self.parameters['indent'] = " " * (len(self.line) + 1)
            else:
                self.line = ""
                self.parameters['indent'] = ""
            authors = utils.get_formatted_authors(publication["authors"],
                                                  complete=self.parameters['all_authors'])
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
            if self.parameters["doi_url"]:
                doi_url = publication.get("doi")
                if doi_url:
                    self.write_fragment(constants.DOI_URL % doi_url)
            if self.parameters["pmid_url"]:
                pmid_url = publication.get("pmid")
                if pmid_url:
                    self.write_fragment(constants.PUBMED_URL % pmid_url)
            if self.line:
                self.text.write(self.line)
                self.text.write("\n")
            self.text.write("\n")

    def write_fragment(self, fragment, comma=True):
        "Write the given fragment to the line."
        if comma:
            self.line += ","
        parts = fragment.split()
        for part in parts:
            length = len(self.line) + len(part) + 1
            if self.parameters["maxline"] is not None and \
               length > self.parameters["maxline"]:
                self.text.write(self.line + "\n")
                self.line = self.parameters["indent"] + part
            else:
                if self.line:
                    self.line += " "
                self.line += part

    def get_content(self):
        "Get the file contents as bytes."
        content = self.text.getvalue()
        return content.encode(self.parameters["encoding"], "backslashreplace")
