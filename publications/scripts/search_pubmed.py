"""Search PubMed using specified criteria and import the references
setting them as unverified.
Labels are applied according to the specified account.
"""

from __future__ import print_function

import sys
import time

import requests

from publications import constants
from publications import pubmed
from publications import utils
from publications.publication import PublicationSaver

DELAY = 1.0


def get_args():
    parser = utils.get_command_line_parser(
        usage='usage: %prog [options] account',
        description='Search PubMed and import references.')
    parser.add_option('-n', '--noninteractive',
                      action='store_false', dest='interactive', default=True,
                      help='do not ask for confirmation for each publication')
    parser.add_option('-d', '--dry-run',
                      action='store_true', dest='dry_run', default=False,
                      help='search but do not import')
    parser.add_option('-y', '--delay',
                      action='store', dest='delay', default=DELAY,
                      help='delay between each PubMed fetch (seconds)')
    parser.add_option('-a', '--author',
                      action='store', dest='author', default=None,
                      metavar='AUTHOR', help='author, e.g. "Kraulis P"')
    parser.add_option('-f', '--affiliation',
                      action='store', dest='affiliation', default=None,
                      metavar='AFFILIATION',
                      help='affiliaton, e.g. SciLifeLab')
    parser.add_option('-p', '--published',
                      action='store', dest='published', default=None,
                      metavar='DATE', help='publication date')
    parser.add_option('-t', '--title',
                      action='store', dest='title', default=None,
                      metavar='TITLE', help='title of publication')
    parser.add_option('-x', '--exclude_title',
                      action='store', dest='exclude_title', default=None,
                      metavar='TITLE', help='require not in title')
    parser.add_option('-j', '--journal',
                      action='store', dest='journal', default=None,
                      metavar='JOURNAL', help='journal name')
    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.print_help()
        sys.exit()
    return (options, args)

def search_pubmed(db, email,
                  interactive=False,
                  dry_run=False,
                  delay=DELAY,
                  author=None,
                  affiliation=None,
                  published=None,
                  journal=None,
                  title=None,
                  exclude_title=None):
    account = utils.get_account(db, email)
    pmids = set(pubmed.search(author=author,
                              affiliation=affiliation,
                              published=published,
                              journal=journal,
                              title=title,
                              exclude_title=exclude_title))
    if interactive:
        print(len(pmids), 'publications found in PubMed search')
    trashed = set()
    for pmid in pmids:
        if utils.get_trashed(db, pmid):
            trashed.add(pmid)
    if interactive:
        print(len(trashed), 'already trashed')
    pmids = pmids.difference(trashed)
    not_imported = set()
    for pmid in pmids:
        try:
            doc = utils.get_publication(db, pmid, unverified=True)
        except KeyError:
            not_imported.add(pmid)
    if interactive:
        print(len(pmids) - len(not_imported), 'already imported')
    if dry_run:
        return
    try:
        delay = -abs(float(delay))
    except (TypeError, ValueError):
        delay = -DELAY
    for pmid in not_imported:
        if delay > 0.0:
            time.sleep(delay)
        elif delay < 0.0:
            delay = -delay
        publication = pubmed.fetch(pmid)
        if interactive:
            print()
            print(publication['title'])
            print(utils.get_formatted_authors(publication))
            print(utils.get_formatted_journal(publication, html=False))
            answer = raw_input('import this publication ? [Y/n] > ')
            if answer and answer.lower()[0] != 'y':
                continue
        with PublicationSaver(doc=publication, db=db, account=account) as saver:
            if account['role'] == constants.CURATOR:
                saver['labels'] = sorted(account['labels'])
            else:
                saver['labels'] = []
        if interactive:
            print('imported as unverified')


if __name__ == '__main__':
    (options, args) = get_args()
    utils.load_settings(filepath=options.settings)
    db = utils.get_db()
    try:
        search_pubmed(db, args[0],
                      interactive=options.interactive,
                      dry_run=options.dry_run,
                      delay=options.delay,
                      author=options.author,
                      affiliation=options.affiliation,
                      published=options.published,
                      journal=options.journal,
                      title=options.title,
                      exclude_title=options.exclude_title)
    except KeyError, msg:
        sys.exit("Error: %s" % msg)
