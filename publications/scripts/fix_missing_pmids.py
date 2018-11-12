"Try to fix missing PMID in all publications by searching for title."

from __future__ import print_function

from publications.publication import PublicationSaver
from publications import pubmed
from publications import utils


DELAY = 2.0

def fix_missing_pmids(db, jump=0):
    view = db.view('publication/no_pmid', include_docs=True)
    for pos, item in enumerate(view):
        if pos < jump: continue
        title = item.doc['title']
        print("[%s]" % pos, title)
        pmids = pubmed.search(title=title, delay=DELAY)
        if len(pmids) == 1:
            with PublicationSaver(doc=item.doc, db=db) as saver:
                saver['pmid'] = pmids[0]
            print('updated', pmids[0])
        print()


if __name__ == '__main__':
    parser = utils.get_command_line_parser(
        'Fix missing PMID in all publications by searching for title.')
    parser.add_argument('-j', '--jump',
                        action='store', dest='jump', type=int, default=0,
                        help='jump over the first number of publications')
    args = parser.parse_args()
    utils.load_settings(filepath=args.settings)
    db = utils.get_db()
    fix_missing_pmids(db, jump=args.jump)
