"Fix missing PMID in all publications by searching for title."

from __future__ import print_function

from publications.publication import PublicationSaver
from publications import pubmed
from publications import utils


DELAY = 2.0

def fix_missing_pmids(db):
    view = db.view('publication/no_pmid', include_docs=True)
    for item in view:
        title = item.doc['title']
        print(title)
        pmids = pubmed.search(title=title, delay=DELAY)
        if len(pmids) == 1:
            with PublicationSaver(doc=item.doc, db=db) as saver:
                saver['pmid'] = pmids[0]
            print('updated', pmids[0])
        print()

def get_args():
    parser = utils.get_command_line_parser(
        'Fx missing PMID in all publications by searching for title.')
    return parser.parse_args()


if __name__ == '__main__':
    args = get_args()
    utils.load_settings(filepath=args.settings)
    db = utils.get_db()
    fix_missing_pmids(db)
