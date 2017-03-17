"Create an admin account in the database."

from __future__ import print_function

import sys
import getpass

from publications import constants
from publications import utils
from publications.account import AccountSaver


def get_args():
    parser = utils.get_command_line_parser(description=
        'Create a new admin account account.')
    return parser.parse_args()

def create_admin(email, password):
    with AccountSaver(db=utils.get_db()) as saver:
        saver.set_email(email)
        saver['owner'] = email
        saver.set_password(password)
        saver['role'] = constants.ADMIN
    print('Created admin account', email)


if __name__ == '__main__':
    (options, args) = get_args()
    utils.load_settings(filepath=options.settings)
    email = raw_input('Email address (=account identifier) > ')
    if not email:
        sys.exit('Error: no email address provided')
    password = getpass.getpass('Password > ')
    if not password:
        sys.exit('Error: no password provided')
    create_admin(email, password)
