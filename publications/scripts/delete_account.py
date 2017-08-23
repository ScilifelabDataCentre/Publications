"Delete an account, if possible."

from __future__ import print_function

import sys

from publications import constants
from publications import utils


def get_args():
    parser = utils.get_command_line_parser(
        "Delete the account, if possible.")
    parser.add_argument('email', type=str, nargs=1,
                        help='Account (email address) to delete.')
    return parser.parse_args()

def delete_account(db, email):
    try:
        account = utils.get_account(db, email)
    except KeyError:
        sys.exit('no such account')
    if account['role'] == constants.ADMIN:
        sys.exit('cannot delete an admin account')
    owned = []
    for doc in utils.get_docs(db, 'publication/modified'):
        if doc.get('account') == email:
            owned.append(doc['_id'])
    if owned:
        print("owns %i publication references" % len(owned))
        for iuid in owned:
            print(iuid)
        sys.exit('cannot delete account')
    logs = utils.get_docs(db, 'log/account',
                          key=[email, ''], 
                          last=[email, constants.CEILING])
    print(len(logs), 'edit log entries')
    for log in logs:
        db.delete(log)
    logs = utils.get_docs(db, 'log/doc',
                          key=[account['_id'], ''],
                          last=[account['_id'], constants.CEILING])
    print(len(logs), 'account log entries')
    for log in logs:
        db.delete(log)
    db.delete(account)
    print('deleted account')


if __name__ == '__main__':
    args = get_args()
    utils.load_settings(filepath=args.settings)
    db = utils.get_db()
    delete_account(db, args.email[0])
