"Fix all normalized author names to be lower case in publications."

from __future__ import print_function

from publications import constants
from publications import settings
from publications import utils

def get_args():
    parser = utils.get_command_line_parser(
        'Fix all normalized author names to be lower case in publications.')
    return parser.parse_args()

def fix_publications_normalized_lower(db):
    "Fix all normalized author names to be lower case in publications."
    for row in db.view('publication/modified', include_docs=True):
        doc = row.doc
        authors = doc['authors']
        for author in authors:
            for key in ['family_normalized',
                        'given_normalized',
                        'initials_normalized']:
                value = author[key]
                if value:
                    author[key] = value.lower()
                else:
                    author[key] = ''
        db.save(doc)


if __name__ == '__main__':
    args = get_args()
    utils.load_settings(filepath=args.settings)
    db = utils.get_db()
    fix_publications_normalized_lower(db)
