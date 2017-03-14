""" OrderPortal: Dump the database into a tar file.
The settings file may be given as the first command line argument,
otherwise it is obtained as usual.
The dump file will be called 'dump_{ISO date}.tar.gz' using today's date.
If the filename does not contain any directory specification (either relative
or absolute), then the dump file is created in the directory specified
by the BACKUP_DIR variable in the settings. 
"""

from __future__ import print_function, absolute_import

import cStringIO
import json
import os
import sys
import tarfile
import time

import couchdb

from orderportal import constants
from orderportal import settings
from orderportal import utils


def get_command_line_parser():
    parser = utils.get_command_line_parser(description=
        'Dump all data into a tar file.')
    parser.add_option('-d', '--dumpfile',
                      action='store', dest='dumpfile',
                      metavar='DUMPFILE', help='name of dump file')
    return parser

def dump(db, filepath):
    """Dump contents of the database to a tar file, optionally gzip compressed.
    Skip any entity that does not contain a doctype field.
    """
    count_items = 0
    count_files = 0
    if filepath.endswith('.gz'):
        mode = 'w:gz'
    else:
        mode = 'w'
    outfile = tarfile.open(filepath, mode=mode)
    for key in db:
        doc = db[key]
        # Only documents that explicitly belong to the application
        if doc.get(constants.DOCTYPE) is None: continue
        del doc['_rev']
        info = tarfile.TarInfo(doc['_id'])
        data = json.dumps(doc)
        info.size = len(data)
        outfile.addfile(info, cStringIO.StringIO(data))
        count_items += 1
        for attname in doc.get('_attachments', dict()):
            info = tarfile.TarInfo("{0}_att/{1}".format(doc['_id'], attname))
            attfile = db.get_attachment(doc, attname)
            if attfile is None:
                data = ''
            else:
                data = attfile.read()
                attfile.close()
            info.size = len(data)
            outfile.addfile(info, cStringIO.StringIO(data))
            count_files += 1
    outfile.close()
    print('dumped', count_items, 'items and',
          count_files, 'files to', filepath, file=sys.stderr)

def undump(db, filepath):
    """Reverse of dump; load all items from a tar file.
    Items are just added to the database, ignoring existing items.
    """
    count_items = 0
    count_files = 0
    attachments = dict()
    infile = tarfile.open(filepath, mode='r')
    for item in infile:
        itemfile = infile.extractfile(item)
        itemdata = itemfile.read()
        itemfile.close()
        if item.name in attachments:
            # This relies on an attachment being after its item in the tarfile.
            db.put_attachment(doc, itemdata, **attachments.pop(item.name))
            count_files += 1
        else:
            doc = json.loads(itemdata)
            # If the account already exists, do not load document.
            if doc[constants.DOCTYPE] == constants.ACCOUNT:
                rows = db.view('account/email', key=doc['email'])
                if len(list(rows)) != 0: continue
            atts = doc.pop('_attachments', dict())
            # Overwrite meta documents
            if doc[constants.DOCTYPE] == constants.META:
                try:
                    doc2 = db[doc['_id']]
                except couchdb.ResourceNotFound:
                    pass
                else:
                    doc2.update(doc)
                    doc = doc2
            db.save(doc)
            count_items += 1
            for attname, attinfo in atts.items():
                key = "{0}_att/{1}".format(doc['_id'], attname)
                attachments[key] = dict(filename=attname,
                                        content_type=attinfo['content_type'])
    infile.close()
    print('undumped', count_items, 'items and',
          count_files, 'files from', filepath, file=sys.stderr)


if __name__ == '__main__':
    parser = get_command_line_parser()
    (options, args) = parser.parse_args()
    utils.load_settings(filepath=options.settings)
    db = utils.get_db()
    if options.dumpfile:
        filepath = options.dumpfile
    else:
        filepath = "dump_{0}.tar.gz".format(time.strftime("%Y-%m-%d"))
    if os.path.basename(filepath) == filepath:
        try:
            filepath = os.path.join(settings['BACKUP_DIR'], filepath)
        except KeyError:
            pass
    dump(db, filepath)
