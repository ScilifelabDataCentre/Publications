"Create the curators and their labels from the CSV file."

from __future__ import print_function

import csv

from publications import constants
from publications import utils
from publications.account import AccountSaver
from publications.label import LabelSaver


INFILENAME = 'Publikationer Faciliteten anv 2015 pmids.csv'
FACILITY_POS = 2
CURATOR_POS = 11

def get_args():
    parser = utils.get_command_line_parser(
        'Create the curators and their labels'
        '  in the database from the CSV file.')
    return parser.parse_args()

def get_curators():
    "Get the curators and their labels from the CSV file."
    curators = dict()
    with open(INFILENAME, 'rb') as infile:
        reader = csv.reader(infile)
        reader.next()
        for record in reader:
            email = record[CURATOR_POS].strip()
            # Mattias has taken this task over from Per.
            if email == 'per.kraulis@scilifelab.se':
                email = 'mattias.ormestad@scilifelab.se'
            label = record[FACILITY_POS].strip()
            if email and label:
                label = unicode(label, 'utf-8')
                curators.setdefault(email.lower(), set()).add(label)
    return curators

def create_curators(curators):
    "Create the given curators and their labels."
    labels = set()
    for ls in curators.values():
        labels.update(ls)

    for label in sorted(labels):
        try:
            utils.get_label(db, label)
        except KeyError:
            with LabelSaver(db=db, account=account) as saver:
                saver.set_value(label)
            print('created label', label)

    for email in sorted(curators):
        print(email, curators[email])
        try:
            doc = utils.get_account(db, email)
        except KeyError:
            with AccountSaver(db=db, account=account) as saver:
                saver.set_email(email)
                saver['owner'] = email
                saver['role'] = constants.CURATOR
                saver['labels'] = sorted(curators[email])
            print('created', email)
        else:
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
    create_curators(curators)
