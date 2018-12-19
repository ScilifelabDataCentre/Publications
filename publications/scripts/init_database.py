"""Initialize the CouchDB database instance.

NOTE: The CouchDB database must exist.

1) Wipes out the old database, using the slow method of deleting
   each document in turn. Consider instead doing database delete
   from the CouchDB interface.
2) Loads the design documents (view index definitions).
"""

from __future__ import print_function

from publications import utils


def init_database(db):
    "Initialize the database; load design documents."
    print('wiping out database (slow method)...')
    for doc in db: del db[doc]
    print('wiped out database')
    utils.initialize(db)


if __name__ == '__main__':
    import sys
    parser = utils.get_command_line_parser(description=
        'Initialize the database, deleting all old data.')
    parser.add_argument('-f', '--force',
                        action='store_true', dest='force', default=False,
                        help='force deletion; skip question')
    args = parser.parse_args()
    utils.load_settings(filepath=args.settings)
    if not args.force:
        response = raw_input('about to delete everything; really sure? [n] > ')
        if not utils.to_bool(response):
            sys.exit('aborted')
    init_database(utils.get_db())
