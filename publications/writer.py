"Write set of publications to a file."

import csv
import io

import xlsxwriter

from publications import constants
from publications import settings
from publications import utils


_QUOTING = dict(all=csv.QUOTE_ALL,
                minimal=csv.QUOTE_MINIMAL,
                nonnumeric=csv.QUOTE_NONNUMERIC,
                none=csv.QUOTE_NONE)

class Writer:
    "Abstract writer of publications to a file."

    def __init__(self, db, app):
        self.db = db
        self.app = app
        self.parameters = {"all_authors": False,
                           "issn": False,
                           "single_label": False}

    def set_parameter(self, key, value=None):
        if value:
            self.parameters[key] = value

    def absolute_reverse_url(self, name, *args, **query):
        if name is None:
            path = ""
        else:
            path = self.app.reverse_url(name, *args, **query)
        return settings["BASE_URL"].rstrip("/") + path

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

    def get_content(self):
        "Get the file contents as bytes."
        raise NotImplementedError


class CsvWriter(Writer):
    "Write publications to a CSV file."

    def __init__(self, db, app,
                 delimiter=",", quoting="nonnumeric", encoding="utf-8"):
        super().__init__(db, app)
        self.csvbuffer = io.StringIO()
        quoting = _QUOTING.get(quoting.lower(), csv.QUOTE_MINIMAL)
        self.parameters["encoding"] = encoding
        self.writer = csv.writer(self.csvbuffer,
                                 delimiter=delimiter,
                                 quoting=quoting)

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
        return content.encode(self.parameters["encoding"], "ignore")


class XlsxWriter(Writer):
    "Write publications to an XLSX (Excel) file."

    def __init__(self, db, app):
        super().__init__(db, app)
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
            self.ws.set_column(14, 15, 20) # Qualifiers, IUID
        else:
            self.ws.set_column(9, 9, 30) # DOI
            self.ws.set_column(10, 10, 10) # PMID
            self.ws.set_column(11, 11, 30) # Labels
            self.ws.set_column(12, 13, 20) # Qualifiers, IUID
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
    pass
