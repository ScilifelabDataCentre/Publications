"Fix all labels to be lookup with label as key, qualifier as value."

from __future__ import print_function

from publications import constants
from publications import settings
from publications import utils

def get_args():
    parser = utils.get_command_line_parser(
        'Fix all labels to be lookup with label as key, qualifier as value.')
    return parser.parse_args()

def fix_label_qualifiers(db):
    "Fix all labels to be lookup with label as key, qualifier as value."
    for row in db.view('publication/modified', include_docs=True):
        doc = row.doc
        labels = doc.get('labels') or []
        doc['labels'] = dict([(l, None) for l in labels])
        db.save(doc)


if __name__ == '__main__':
    args = get_args()
    utils.load_settings(filepath=args.settings)
    db = utils.get_db()
    fix_label_qualifiers(db)
