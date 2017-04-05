"Set the password for an account."

from __future__ import print_function

import sys
import getpass

from publications import constants
from publications import utils
from publications.account import AccountSaver


def get_args():
    parser = utils.get_command_line_parser(
        usage='usage: %prog [options] account',
        description='Set the password for an account.')
    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.print_help()
        sys.exit()
    return (options, args)

def set_password(db, email, password):
    account = utils.get_account(db, email)
    with AccountSaver(doc=account, db=db) as saver:
        saver.set_password(password)
    print("Set password for", email)


if __name__ == '__main__':
    (options, args) = get_args()
    utils.load_settings(filepath=options.settings)
    db = utils.get_db()
    password = getpass.getpass('Password > ')
    if not password:
        sys.exit('Error: no password provided')
    if password != getpass.getpass('Password again > '):
        sys.exit('Error: passwords did not match')
    set_password(db, args[0], password)
