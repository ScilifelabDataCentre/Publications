"List all xrefs currently in database in files."

from publications import utils


def list_xrefs(db):
    "Write all xrefs currently in database into files."
    view = db.view('publication/modified', include_docs=True)
    dbs = dict()
    for item in view:
        for xref in item.doc.get('xrefs', []):
            try:
                dbs[xref["db"]].add(xref["key"])
            except KeyError:
                dbs[xref["db"]] = set([xref["key"]])
    for db, keys in dbs.items():
        if db.startswith("http"):
            print(db, keys)
        else:
            with open(f"{db}.list", "w") as outfile:
                for key in sorted(keys):
                    outfile.write(key)
                    outfile.write("\n")


if __name__ == '__main__':
    parser = utils.get_command_line_parser('List all xrefs in files.')
    args = parser.parse_args()
    utils.load_settings(filepath=args.settings)
    db = utils.get_db()
    list_xrefs(db)
