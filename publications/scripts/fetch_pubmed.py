"""Fetch publicaton references from PubMed given PMIDs.
An account must be specified, and labels are applied accordingly.
The publications are set as verified.
"""

from __future__ import print_function

import sys

import requests

from publications import constants
from publications import pubmed
from publications import utils
from publications.publication import PublicationSaver


def get_args():
    parser = utils.get_command_line_parser(
        usage='usage: %prog [options] account pmid [pmid...]',
        description='Fetch publication references from PubMed given PMIDs.')
    (options, args) = parser.parse_args()
    if len(args) < 2:
        parser.print_help()
        sys.exit(1)
    return (options, args)

def fetch_pmid(db, account, pmid):
    """Fetch the publication reference given the PMID and the account.
    Update the existing record, if any. 
    Labels are applied according to the account.
    """
    if utils.get_blacklisted(db, pmid):
        print(pmid, 'is blacklisted!')
        return
    for viewname in ['publication/pmid', 'publication/pmid_unverified']:
        try:
            old = utils.get_doc(db, pmid, viewname=viewname)
            break
        except KeyError:
            pass
    else:
        old = None
    try:
        new = pubmed.fetch(pmid)
    except (IOError, requests.exceptions.Timeout):
        print(pmid, 'could not be fetched')
    if old:
        with PublicationSaver(old, db=db, account=account) as saver:
            for key in new:
                saver[key] = new[key]
            if account['role'] == constants.CURATOR:
                labels = set(account.get('labels', []))
            else:
                labels = set()
            labels.update(old['labels'])
            saver['labels'] = sorted(labels)
            saver['verified'] = True
        print(pmid, 'updated')
    else:
        with PublicationSaver(new, db=db, account=account) as saver:
            saver['verified'] = True
            if account['role'] == constants.CURATOR:
                saver['labels'] = sorted(account.get('labels', []))
            else:
                saver['labels'] = []
        print(pmid, 'fetched')


if __name__ == '__main__':
    (options, args) = get_args()
    utils.load_settings(filepath=options.settings)
    db = utils.get_db()
    try:
        account = utils.get_doc(db, args[0], viewname='account/email')
    except KeyError:
        sys.exit("Error: no such account: %s" % args[0])
    for pmid in args[1:]:
        if constants.PMID_RX.match(pmid):
            fetch_pmid(db, account, pmid)
        else:
            print('Error:', pmid, 'is not a PMID')

