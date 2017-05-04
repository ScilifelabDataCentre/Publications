"Create the labels from the CSV file."

from __future__ import print_function

import csv

from publications import constants
from publications import utils
from publications.account import AccountSaver
from publications.label import LabelSaver


INFILENAME = 'publikationer faciliteter 2010-2014 pmid v2.csv'
PLATFORM_POS = 1
FACILITY_POS = 2

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
        'Create the curators and their labels'
        '  in the database from the CSV file.')
    parser.add_argument('-d', '--dryrun',
                        action='store_true', dest='dryrun', default=False,
                        help='Dry run; database not updated.')
    return parser.parse_args()

def get_labels():
    "Get the labels from the CSV file."
    labels = set()
    with open(INFILENAME, 'rb') as infile:
        reader = csv.reader(infile)
        reader.next()
        for record in reader:
            label = record[FACILITY_POS].strip()
            if not label or label.lower() == 'n/a':
                label = record[PLATFORM_POS].strip()
            labels.add(RENAME_LABEL.get(label, label))
    return labels

def create_labels(labels, dryrun=False):
    "Create the given labels."
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


if __name__ == '__main__':
    args = get_args()
    utils.load_settings(filepath=args.settings)
    db = utils.get_db()
    account = utils.get_account(db, 'per.kraulis@scilifelab.se')
    labels = get_labels()
    print(len(labels))
    create_labels(labels, dryrun=args.dryrun)
