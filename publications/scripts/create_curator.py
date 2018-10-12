"Create an account with the 'curator' role."

from __future__ import print_function

import sys

from publications import constants
from publications import utils
from publications.account import AccountSaver


def get_args():
    parser = utils.get_command_line_parser(
        description='Create a new curator account.')
    return parser.parse_args()

def create_curator(db, email, labels):
    with AccountSaver(db=db) as saver:
        saver.set_email(email)
        saver['owner'] = email
        saver['role'] = constants.CURATOR
        saver['labels'] = labels
    print("Created 'curator' role account", email)
    print('NOTE: No email sent!')


if __name__ == '__main__':
    args = get_args()
    utils.load_settings(filepath=args.settings)
    db = utils.get_db()
    email = raw_input('Email address (=account identifier) > ')
    if not email:
        sys.exit('Error: no email address provided')
    labels = []
    while True:
        label = raw_input('Give label > ')
        label = label.strip()
        if not label: break
        try:
            doc = utils.get_label(db, label)
        except KeyError:
            print('no such label:', label)
        else:
            labels.append(label)
    create_curator(db, email, labels)
