"""Read a file containing mapping of ISSN to ISSN-L
and update the journal documents in the database accordingly.
"""

from publications.journal import JournalSaver
from publications import utils


def add_issn_l(db, issnfile, dryrun=False):
    view = db.view('journal/issn', include_docs=True)
    journals = {}               # Key: ISSN, value: journal document
    for item in view:
        journals[item.key] = item.doc
    updated = []
    count = 0
    different = 0
    with open(issnfile) as infile:
        infile.readline()       # Skip header
        for line in infile:
            parts = line.split()
            if len(parts) < 2: continue
            issn = parts[0]
            issn_l = parts[1]
            count += 1
            if issn != issn_l: different += 1
            try:
                journal = journals[issn]
            except KeyError:
                try:
                    journal = journals[issn_l]
                except KeyError:
                    pass
                else:
                    if journal.get('issn') != issn or \
                       journal.get('issn-l') != issn_l:
                        if not dryrun:
                            with JournalSaver(doc=journal, db=db) as saver:
                                saver["issn"] = issn
                                saver["issn-l"] = issn_l
                        updated.append(journal)
            else:
                if journal.get('issn-l') != issn_l:
                    if not dryrun:
                        with JournalSaver(doc=journal, db=db) as saver:
                            saver["issn-l"] = issn_l
                    updated.append(journal)
    if dryrun:
        print('NOTE: dry run! No changes made.')
    print('count', count)
    print('different', different)
    print('updated', len(updated))


if __name__ == '__main__':
    import sys
    parser = utils.get_command_line_parser(
        'Add ISSN-L to journals from file mapping ISSN to ISSN-L')
    parser.add_argument('-f', '--issnfile',
                      action='store', dest='issnfile',
                      metavar='ISSNFILE', help='path of ISSN to ISSN-L file')
    parser.add_argument('-d', '--dryrun',
                        action='store_true', dest='dryrun', default=False)
    args = parser.parse_args()
    utils.load_settings(filepath=args.settings)
    if not args.issnfile:
        sys.exit('Error: no ISSN to ISSN-L file given')
    db = utils.get_db()
    add_issn_l(db, args.issnfile, args.dryrun)
