"""Check for duplicates based on comparing 4 longest words in the title.
A fast and dirty comparison algorithm. Will produce som false positives.
"""

from __future__ import print_function

from publications import utils


def check_duplicates(db):
    view = db.view('publication/modified', include_docs=True)
    lookup = {}
    for item in view:
        title = item.doc['title']
        ascii_title = utils.to_ascii(title).lower()
        parts = sorted(ascii_title.split(), key=len, reverse=True)
        key = ' '.join(parts[:4])
        if key in lookup:
            print(item.doc.get('pmid'),
                  item.doc.get('doi'),
                  title)
            print(lookup[key].get('pmid'),
                  lookup[key].get('doi'),
                  lookup[key]['title'])
            print()
        else:
            lookup[key] = dict(pmid=item.doc.get('pmid'),
                               doi=item.doc.get('doi'),
                               title=title)


if __name__ == '__main__':
    parser = utils.get_command_line_parser(
        'Check for duplicated based on title.')
    args = parser.parse_args()
    utils.load_settings(filepath=args.settings)
    db = utils.get_db()
    check_duplicates(db)
