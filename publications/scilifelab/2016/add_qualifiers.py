"Add label qualifier (Service, Collaboration, Tech Devel) to publications."

from __future__ import print_function

import csv

from publications import constants
from publications import settings
from publications import utils
from publications.label import LabelSaver
from publications.account import AccountSaver
from publications.publication import PublicationSaver

INFILE = 'Facility publications 2016 pmids v3.csv'
OUTFILE = 'unhandled.csv'
PLATFORM_POS = 1
FACILITY_POS = 2
QUALIFIER_POS = 6
DOI_POS = 3
PMID_POS = 12

QUALIFIERS = set(['Service', 'Collaborative', 'Technology development'])

def get_args():
    parser = utils.get_command_line_parser(
        "Add label qualifier (Service, Collaboration, Tech Devel) to publications.")
    return parser.parse_args()

def add_qualifier(db):
    with open(INFILE, 'rb') as infile:
        reader = csv.reader(infile)
        reader.next()
        for record in reader:
            qualifier = record[QUALIFIER_POS].strip() or None
            if qualifier and qualifier not in QUALIFIERS:
                print('bad qualifier >>>', record)
                continue
            facility = unicode(record[FACILITY_POS], 'utf-8')
            platform = unicode(record[PLATFORM_POS], 'utf-8')
            doi = record[DOI_POS].lower()
            doi = doi.strip()
            if ':' in doi:
                doi = doi[doi.index(':')+1:].strip()
            if doi.lower() == 'n/a':
                doi = ''
            pmid = record[PMID_POS].strip()
            if not doi and not pmid:
                print('no DOI or PMID >>>', record)
                continue
            doi_doc = None
            if doi:
                rows = list(db.view('publication/doi',
                                    include_docs=True, key=doi))
                if len(rows) == 1:
                    doi_doc = rows[0].doc
            pmid_doc = None
            if pmid:
                rows = list(db.view('publication/pmid',
                                    include_docs=True, key=pmid))
                if len(rows) == 1:
                    pmid_doc = rows[0].doc
            if doi_doc:
                with PublicationSaver(doi_doc, db=db) as saver:
                    labels = saver['labels'].copy()
                    for label in labels:
                        if label in (facility, platform):
                            labels[label] = qualifier
                            break
                    saver['labels'] = labels
            elif pmid_doc:
                with PublicationSaver(pmid_doc, db=db) as saver:
                    labels = saver['labels'].copy()
                    for label in labels:
                        if label in (facility, platform):
                            labels[label] = qualifier
                            break
                    saver['labels'] = labels


if __name__ == '__main__':
    args = get_args()
    utils.load_settings(filepath=args.settings)
    db = utils.get_db()
    add_qualifier(db)
