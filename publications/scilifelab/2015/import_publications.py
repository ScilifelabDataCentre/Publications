"Import the publications from the CSV file. Skip those without PMID."

from __future__ import print_function

import csv

from publications import utils
from publications import pubmed
from publications.publication import PublicationSaver

INFILENAME = 'Publikationer Faciliteten anv 2015 pmids.csv'
FACILITY_POS = 2
PMID_POS = 14
DIRNAME = 'entries'
DELAY = 1.0

def get_args():
    parser = utils.get_command_line_parser(
        'Import the publications from the CSV file.'
        ' Skip those without PMID.')
    parser.add_argument('-a', '--account', 
                        action='store', dest='account',
                        default='per.kraulis@scilifelab.se',
                        help='Email address of account to import data as.')
    return parser.parse_args()

def import_publications(db, account):
    with open(INFILENAME, 'rb') as infile:
        reader = csv.reader(infile)
        reader.next()
        count = 0
        count_none = 0
        for record in reader:
            pmid = record[PMID_POS].strip()
            if not pmid or pmid.startswith('['):
                count_none += 1
                continue
            print(pmid)
            label = unicode(record[FACILITY_POS].strip(), 'utf-8')
            try:
                publ = utils.get_publication(db, pmid, unverified=True)
            except KeyError:
                new = pubmed.fetch(pmid, dirname=DIRNAME, delay=DELAY)
                count += 1
                with PublicationSaver(new, db=db, account=account) as saver:
                    if label:
                        saver['labels'] = [label]
                    else:
                        saver['labels'] = []
            else:
                labels = set(publ['labels'])
                with PublicationSaver(publ, db=db, account=account) as saver:
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
