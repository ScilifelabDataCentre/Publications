"Display all xrefs currently in database."

from publications import utils


def display_xrefs(db):
    "Display all xrefs currently in database."
    view = db.view('publication/modified', include_docs=True)
    dbs = set()
    for item in view:
        for xref in item.doc.get('xrefs', []):
            print(xref)
            dbs.add(xref['db'])
    print(', '.join(dbs))

if __name__ == '__main__':
    parser = utils.get_command_line_parser('Display all xrefs.')
    args = parser.parse_args()
    utils.load_settings(filepath=args.settings)
    db = utils.get_db()
    display_xrefs(db)
