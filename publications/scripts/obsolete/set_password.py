"Set the password for an existing account."

import getpass

from publications import constants
from publications import utils
from publications.account import AccountSaver


def get_args():
    parser = utils.get_command_line_parser(
        description='Set the password for an account.')
    parser.add_argument('account', action='store',
                        help='Account to set password for.')
    return parser.parse_args()

def set_password(db, email):
    account = utils.get_account(db, email)
    password = getpass.getpass('Password > ')
    if not password:
        raise ValueError('Error: no password provided')
    if password != getpass.getpass('Password again > '):
        raise ValueError('Error: passwords did not match')
    with AccountSaver(doc=account, db=db) as saver:
        saver.set_password(password)
    print("Set password for", email)


if __name__ == '__main__':
    args = get_args()
    utils.load_settings(filepath=args.settings)
    db = utils.get_db()
    set_password(db, args.account)
