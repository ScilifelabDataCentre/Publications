"Create an account with the 'admin' role."

import sys
import getpass

from publications import constants
from publications import utils
from publications.account import AccountSaver


def get_args():
    parser = utils.get_command_line_parser(
        description='Create a new admin account.')
    return parser.parse_args()

def create_admin(db, email, password):
    with AccountSaver(db=db) as saver:
        saver.set_email(email)
        saver['owner'] = email
        saver.set_password(password)
        saver['role'] = constants.ADMIN
        saver['labels'] = []
    print("Created 'admin' role account", email)


if __name__ == '__main__':
    args = get_args()
    utils.load_settings(filepath=args.settings)
    db = utils.get_db()
    email = input('Email address (=account identifier) > ')
    if not email:
        sys.exit('Error: no email address provided')
    password = getpass.getpass('Password > ')
    if not password:
        sys.exit('Error: no password provided')
    if password != getpass.getpass('Password again > '):
        sys.exit('Error: passwords did not match')
    create_admin(db, email, password)
