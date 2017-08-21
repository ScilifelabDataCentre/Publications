"Fix to remove redundant labels due to different character case."

from __future__ import print_function

from publications import constants
from publications import settings
from publications import utils

def get_args():
    parser = utils.get_command_line_parser(
        'Fix to remove redundant labels due to different character case.')
    return parser.parse_args()

def fix_label_charcase(db):
    "Fix to remove redundant labels due to different character case."
    orig_labels = set([r.key for r in db.view('label/value')])
    labels_lookup = dict([(l.lower(), l) for l in orig_labels])
    for row in db.view('publication/modified', include_docs=True):
        doc = row.doc
        fixed = {}
        orig = doc.get('labels') or {}
        for label, qualifier in orig.items():
            if label in orig_labels:
                if label in fixed:
                    fixed[label] = fixed[label] or qualifier
                else:
                    fixed[label] = qualifier
            elif label.lower() in labels_lookup:
                proper_label = labels_lookup[label.lower()]
                if proper_label in fixed:
                    fixed[proper_label] = fixed[proper_label] or qualifier
                else:
                    fixed[proper_label] = qualifier
            else:
                print("!! mismatch label '%s'" % label, doc['title'])
        if fixed != orig:
            print('orig:', orig)
            print('fixed:', fixed)
            print()
            doc['labels'] = fixed
            db.save(doc)


if __name__ == '__main__':
    args = get_args()
    utils.load_settings(filepath=args.settings)
    db = utils.get_db()
    fix_label_charcase(db)
