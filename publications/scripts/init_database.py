""" Publications: Initialize the order database, directly towards CouchDB.
1) Wipes out the old database.
2) Loads the design documents.
"""

from __future__ import print_function

import sys

import yaml

from publications import constants
from publications import settings
from publications import utils
from publications.scripts.dump import undump
from publications.scripts.load_designs import load_designs


def get_args():
    parser = utils.get_command_line_parser(description=
        'Initialize the database, deleting all old data,'
        ' optionally load from dump file.')
    parser.add_option("-L", "--load",
                      action='store', dest='FILE', default='dump.tar.gz',
                      metavar="FILE", help="filepath of dump file to load")
    parser.add_option("-f", "--force",
                      action='store_true', dest='force', default=False,
                      help='force deletion; skip question')
    return parser.parse_args()

def init_database(dumpfilepath=None):
    db = utils.get_db(create=True)
    print('wiping out database...')
    wipeout_database(db)
    print('wiped out database')
    load_designs(db)
    print('loaded designs')
    if dumpfilepath:
        dumpfilepath = utils.expand_filepath(dumpfilepath)
        try:
            undump(db, dumpfilepath)
        except IOError:
            print('Warning: could not load', dumpfilepath)
    else:
        print('no dump file loaded')

def wipeout_database(db):
    """Wipe out the contents of the database.
    This is used rather than total delete of the database instance, since
    that may require additional privileges, depending on the setup.
    """
    for doc in db:
        del db[doc]


if __name__ == '__main__':
    (options, args) = get_args()
    if not options.force:
        response = raw_input('about to delete everything; really sure? [n] > ')
        if not utils.to_bool(response):
            sys.exit('aborted')
    utils.load_settings(filepath=options.settings)
    init_database(dumpfilepath=options.FILE)
