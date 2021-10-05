"""Load a dump tar file into the CouchDB database.

The settings file may be given as a command line option,
otherwise it is obtained as usual.

The file to load must be given as a command line argument.

NOTE: The dabase instance must exist, and should be empty. If it is not
empty, this script may overwrite existing documents.
"""

import json
import logging
import tarfile

from publications import designs
from publications import utils


def undump(db, filepath):
    """Reverse of dump; load all items from a tar file.
    NOTE: Items are just added to the database. Any existing data may
    be overwritten. Should only be used with an empty database.
    """
    count_items = 0
    count_files = 0
    attachments = dict()
    infile = tarfile.open(filepath, mode="r")
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
            atts = doc.pop("_attachments", dict())
            db.put(doc)
            count_items += 1
            for attname, attinfo in list(atts.items()):
                key = "{0}_att/{1}".format(doc["_id"], attname)
                attachments[key] = dict(filename=attname,
                                        content_type=attinfo["content_type"])
        if count_items % 100 == 0:
            logging.info("%s items loaded...", count_items)
    infile.close()
    designs.regenerate_indexes(db)
    logging.info("undumped %s items and %s files from %s",
                 count_items, count_files, filepath)


if __name__ == "__main__":
    parser = utils.get_command_line_parser(
        "Load tar.gz dump file into the database.")
    parser.add_argument("dumpfile", metavar="FILE", type=str,
                        help="Dump file to load into the database.")
    args =  parser.parse_args()
    utils.load_settings(filepath=args.settings, ignore_logging_filepath=True)
    db = utils.get_db()
    utils.initialize(db)
    undump(db, args.dumpfile)
