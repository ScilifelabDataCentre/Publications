"Go through all publications and compile journals with names and ISSN."

from __future__ import print_function

from publications import constants
from publications import settings
from publications import utils
from publications.journal import JournalSaver

def get_args():
    parser = utils.get_command_line_parser(
        'Compile all journals in publications.')
    return parser.parse_args()

def compile_journals(db):
    "Compile journals as dictionary with key ISSN, list of titles as values."
    result = {}
    for row in db.view('publication/published', include_docs=True):
        journal = row.doc.get('journal')
        title = journal.get('title')
        issn = journal.get('issn') or ''
        if title:
            result.setdefault(issn, set()).add(title)
    return result

def create_journals(db, journals):
    "Create the journal documents."
    for issn, titles in journals.items():
        if not titles:
            titles = [issn]
        for title in titles:
            with JournalSaver(db=db) as saver:
                saver['issn'] = issn
                saver['title'] = title


if __name__ == '__main__':
    args = get_args()
    utils.load_settings(filepath=args.settings)
    db = utils.get_db()
    journals = compile_journals(db)
    create_journals(db, journals)
