"Set all currently loaded publications as verified."

from __future__ import print_function

import csv
import time

from publications import utils
from publications.publication import PublicationSaver

def get_args():
    parser = utils.get_command_line_parser(
        'Set all currently loaded publications as verified.')
    parser.add_argument('-a', '--account', 
                        action='store', dest='account',
                        default='per.kraulis@scilifelab.se',
                        help='Email address of account to import data as.')
    return parser.parse_args()

def set_verified(db, account):
    view = db.view('publication/unverified')
    iuids = [r.id for r in view]
    print(len(iuids))
    for iuid in iuids:
        doc = utils.get_publication(db, iuid, unverified=True)
        print(doc['title'])
        with PublicationSaver(doc, db=db, account=account) as saver:
            saver['verified'] = True


if __name__ == '__main__':
    args = get_args()
    utils.load_settings(filepath=args.settings)
    db = utils.get_db()
    account = utils.get_account(db, args.account)
    set_verified(db, account)
