"Check and fix journals and journals in publications."

from __future__ import print_function

from publications import constants
from publications import settings
from publications import utils
from publications.publication import PublicationSaver
from publications.journal import JournalSaver

def get_args():
    parser = utils.get_command_line_parser(
        'Check journals.')
    return parser.parse_args()

def check_journals(db):
    "Check and fix journals and journals in publications."
    print('checking for duplicate ISSNs and titles...')
    issn_lookup = dict()
    title_lookup = dict()
    for row in db.view('journal/issn', include_docs=True):
        issn = row.key
        title = row.value
        if issn in issn_lookup:
            print('duplicate issn', issn, title, issn_lookup[issn])
        else:
            issn_lookup[issn] = title
        if title in title_lookup:
            print('duplicate title', issn, title, title_lookup[title])
        else:
            title_lookup[title] = issn

    print('correcting journal title in publications...')
    for row in db.view('publication/modified', include_docs=True):
        doc = row.doc
        old_issn = doc['journal'].get('issn')
        old_title = doc['journal'].get('title')
        new_issn = None
        new_title = None
        if old_issn:
            if old_issn not in issn_lookup:
                new_issn = title_lookup.get(old_title)
            else:
                new_issn = old_issn
        else:
            new_issn = title_lookup.get(old_title)
        if new_issn and new_issn != old_issn:
            print(doc['_id'], 'replace', old_issn, 'with', new_issn)
            with PublicationSaver(doc=doc, db=db) as saver:
                journal = doc['journal'].copy()
                journal['issn'] = new_issn
                saver['journal'] = journal

        if old_title:
            if old_issn and old_title not in title_lookup:
                new_title = issn_lookup.get(old_issn)
            else:
                new_title = old_title
        else:
            new_title = issn_lookup.get(old_issn)
        if new_title and new_title != old_title:
            print(doc['_id'], 'replace', old_title, 'with', new_title)
            with PublicationSaver(doc=doc, db=db) as saver:
                journal = doc['journal'].copy()
                journal['title'] = new_title
                saver['journal'] = journal

        if not new_issn:
            print('missing ISSN for', doc['_id'], old_title)
        if not new_title:
            print('missing journal title for', doc['_id'], old_issn)

    print('creating journal entries for novel ISSNs...')
    for row in db.view('publication/issn', reduce=False, include_docs=True):
        doc = row.doc
        issn = doc['journal']['issn']
        title = doc['journal']['title']
        rows = list(db.view('journal/issn', key=issn))
        if not rows:
            print('creating journal', title, issn)
            with JournalSaver(db=db) as saver:
                saver['issn'] = issn
                saver['title'] = title


if __name__ == '__main__':
    args = get_args()
    utils.load_settings(filepath=args.settings)
    db = utils.get_db()
    check_journals(db)
