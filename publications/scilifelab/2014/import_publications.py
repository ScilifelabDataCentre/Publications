"Import the publications from the CSV file. Skip those without PMID."

from __future__ import print_function

import csv

from publications import utils
from publications import pubmed
from publications import crossref
from publications.publication import PublicationSaver

INFILENAME = 'publikationer faciliteter 2010-2014 pmid v3.csv'
PLATFORM_POS = 1
FACILITY_POS = 2
PMID_POS = 12
DOI_POS = 13
DIRNAME = 'entries'
DELAY = 1.0

RENAME_LABEL = dict([('Cell Profiling (KTH)', 'Cell Profiling'),
                     ('Fluorescence Tissue Profiling (KI)',
                      'Fluorescence Tissue Profiling'),
                     ('Fluorescent Correlation Spectroscopy',
                      'Fluorescence Correlation Spectroscopy'),
                     ('Protein and peptide arrays (KTH)',
                      'Protein and peptide arrays'),
                     ('Tissue profiling (UU)',
                      'Tissue profiling')])

def get_args():
    parser = utils.get_command_line_parser(
        'Import the publications from the CSV file.'
        ' Skip those without PMID or DOI.')
    parser.add_argument('-a', '--account', 
                        action='store', dest='account',
                        default='per.kraulis@scilifelab.se',
                        help='Email address of account to import data as.')
    return parser.parse_args()

def import_publications(db, account):
    with open(INFILENAME, 'rb') as infile:
        reader = csv.reader(infile)
        reader.next()
        for record in reader:
            publ = None
            label = unicode(record[FACILITY_POS].strip(), 'utf-8')
            if label.lower() == 'n/a':
                label = unicode(record[PLATFORM_POS].strip(), 'utf-8')
            label = RENAME_LABEL.get(label, label)
            try:
                pmid = record[PMID_POS].strip()
            except IndexError:
                pmid = ''
            if pmid:
                print(pmid)
                try:
                    publ = utils.get_publication(db, pmid, unverified=True)
                except KeyError:
                    publ = pubmed.fetch(pmid, dirname=DIRNAME, delay=DELAY)
            else:
                try:
                    doi = record[DOI_POS].strip()
                except IndexError:
                    doi = ''
                if doi:
                    print(doi)
                    try:
                        publ = utils.get_publication(db, doi, unverified=True)
                    except KeyError:
                        publ = crossref.fetch(doi)
            if publ:
                with PublicationSaver(publ, db=db, account=account) as saver:
                    try:
                        labels = set(publ['labels'])
                    except KeyError:
                        labels = set()
                    if label:
                        labels.add(label)
                    saver['labels'] = sorted(labels)
                    saver['verified'] = True


if __name__ == '__main__':
    args = get_args()
    utils.load_settings(filepath=args.settings)
    db = utils.get_db()
    account = utils.get_account(db, args.account)
    import_publications(db, account)
