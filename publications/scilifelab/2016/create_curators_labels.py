"Create the curators and their labels from the CSV file."

from __future__ import print_function

import csv

from publications import constants
from publications import utils
from publications.account import AccountSaver
from publications.label import LabelSaver


INFILENAME = 'Facility publications 2016 pmids v3.csv'
PLATFORM_POS = 1
FACILITY_POS = 2
CURATOR_POS = 7

def get_args():
    parser = utils.get_command_line_parser(
        'Create the curators and their labels'
        '  in the database from the CSV file.')
    parser.add_argument('-d', '--dryrun',
                        action='store_true', dest='dryrun', default=False,
                        help='Dry run; database not updated.')
    return parser.parse_args()

def get_curators():
    "Get the curators and their labels from the CSV file."
    curators = dict()
    with open(INFILENAME, 'rb') as infile:
        reader = csv.reader(infile)
        reader.next()
        for record in reader:
            email = record[CURATOR_POS].strip().lower()
            label = record[FACILITY_POS].strip()
            if label.lower() == 'n/a':
                label = record[PLATFORM_POS].strip()
            if email and label:
                label = unicode(label, 'utf-8')
                curators.setdefault(email.lower(), set()).add(label)
    return curators

def create_curators(curators, dryrun=False):
    "Create the given curators and their labels."
    labels = set()
    for ls in curators.values():
        labels.update(ls)

    for label in sorted(labels):
        try:
            utils.get_label(db, label)
        except KeyError:
            if dryrun:
                print('would create label', label)
            else:
                with LabelSaver(db=db, account=account) as saver:
                    saver.set_value(label)
                print('created label', label)

    for email in sorted(curators):
        try:
            doc = utils.get_account(db, email)
        except KeyError:
            if dryrun:
                print('would create account', email)
            else:
                with AccountSaver(db=db, account=account) as saver:
                    saver.set_email(email)
                    saver['owner'] = email
                    saver['role'] = constants.CURATOR
                    saver['labels'] = sorted(curators[email])
                print('created account', email)
        else:
            if not dryrun:
                with AccountSaver(doc=doc, db=db, account=account) as saver:
                    saver['role'] = constants.CURATOR
                    saver['labels'] = sorted(curators[email])


if __name__ == '__main__':
    args = get_args()
    utils.load_settings(filepath=args.settings)
    db = utils.get_db()
    account = utils.get_account(db, 'per.kraulis@scilifelab.se')
    curators = get_curators()
    print(len(curators))
    create_curators(curators, dryrun=args.dryrun)
