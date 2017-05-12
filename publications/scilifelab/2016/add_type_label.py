"Add type label (Service, Collaboration, Tech Devel) to publications."

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
DOI_POS = 3
TYPE_POS = 6
PMID_POS = 12

TYPES = set(['Service', 'Collaborative', 'Technology development'])

def get_args():
    parser = utils.get_command_line_parser(
        "Add type label (Service, Collaboration, Tech Devel) to publications.")
    return parser.parse_args()

def create_type_label(db):
    "Create the type labels and set for all non-admin accounts."
    for type_label in TYPES:
        rows = db.view('label/value', key=type_label)
        if len(rows) == 0:
            print('creating label' ,type_label)
            with LabelSaver(db=db) as saver:
                saver.set_value(type_label)
        for row in db.view('account/email', include_docs=True):
            doc = row.doc
            if doc['role'] == constants.ADMIN: continue
            if type_label not in doc['labels']:
                with AccountSaver(doc, db=db) as saver:
                    labels = set(doc['labels'])
                    labels.add(type_label)
                    saver['labels'] = sorted(labels)


def add_type_label(db):
    with open(INFILE, 'rb') as infile:
        reader = csv.reader(infile)
        reader.next()
        for record in reader:
            if record[TYPE_POS] not in TYPES:
                print('type >>>', record)
                continue
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
                    labels = set(saver['labels'])
                    labels.add(record[TYPE_POS])
                    saver['labels'] = sorted(labels)
                    if not saver['pmid'] and pmid:
                        saver['pmid'] = pmid
            elif pmid_doc:
                with PublicationSaver(pmid_doc, db=db) as saver:
                    labels = set(saver['labels'])
                    labels.add(record[TYPE_POS])
                    saver['labels'] = sorted(labels)
                    if not saver['doi'] and doi:
                        saver['doi'] = doi


if __name__ == '__main__':
    args = get_args()
    utils.load_settings(filepath=args.settings)
    db = utils.get_db()
    # create_type_label(db)
    add_type_label(db)
