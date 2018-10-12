"""Fetch publications in bulk given a CSV file with PMID/DOI,
label and qualifier.
"""

from __future__ import print_function

import csv

import requests

from publications import constants
from publications import crossref
from publications import pubmed
from publications import settings
from publications import utils
from publications.publication import PublicationSaver

DELAY = 2.0
ACCOUNT = dict(email='per.kraulis@scilifelab.se')

def get_pmid(db, pmid):
    "Get an existing publication for the PMID."
    try:
        return utils.get_doc(db, pmid, viewname='publication/pmid')
    except KeyError:
        return None

def get_doi(db, doi):
    "Get an existing publication for the DOI."
    try:
        return utils.get_doc(db, doi, viewname='publication/doi')
    except KeyError:
        return None

def fetch_pmid(db, pmid, label, qualifier):
    """Fetch the publication reference given the PMID.
    Update the existing record, if any.
    Apply the given label and qualifier.
    """
    if utils.get_blacklisted(db, pmid):
        print('Error:', pmid, 'is blacklisted!')
        return
    try:
        utils.get_label(db, label)
    except KeyError:
        print('Error:', pmid, 'label', label, 'does not exist')
        return
    if qualifier not in settings['SITE_LABEL_QUALIFIERS']:
        print('Warning:', pmid, 'qualifier', qualifier, 'does not exist')
        qualifier = None        
    old = get_pmid(db, pmid)
    if old:
        with PublicationSaver(old, db=db, account=ACCOUNT) as saver:
            labels = saver.get('labels', {}).copy()
            labels[label] = qualifier
            saver['labels'] = labels
        print(pmid, 'updated')
    else:
        try:
            new = pubmed.fetch(pmid, delay=DELAY)
        except (IOError, ValueError, requests.exceptions.Timeout) as err:
            print('Error:', pmid, 'could not be fetched:', err)
            return
        try:
            old = get_doi(db, new['doi'])
            if not old: raise KeyError
        except KeyError:
            with PublicationSaver(new, db=db, account=ACCOUNT) as saver:
                labels = saver.get('labels', {}).copy()
                labels[label] = qualifier
                saver['labels'] = labels
            print(pmid, 'fetched')
        else:
            with PublicationSaver(old, db=db, account=ACCOUNT) as saver:
                saver['pmid'] = pmid
                labels = saver.get('labels', {}).copy()
                if label:
                    labels[label] = qualifier
                saver['labels'] = labels
            print(pmid, 'set for existing doi)')

def fetch_doi(db, doi, label, qualifier):
    """Fetch the publication reference given the DOI.
    Update the existing record, if any.
    Apply the given label and qualifier.
    """
    if utils.get_blacklisted(db, doi):
        print('Error:', doi, 'is blacklisted!')
        return
    try:
        utils.get_label(db, label)
    except KeyError:
        print('Error:', doi, 'label', label, 'does not exist')
        return
    if qualifier not in settings['SITE_LABEL_QUALIFIERS']:
        print('Warning:', doi, 'qualifier', qualifier, 'does not exist')
        qualifier = None
    old = get_doi(db, doi)
    if old:
        with PublicationSaver(old, db=db, account=ACCOUNT) as saver:
            labels = saver.get('labels', {}).copy()
            labels[label] = qualifier
            saver['labels'] = labels
        print(doi, 'updated')
    else:
        try:
            new = crossref.fetch(doi, delay=DELAY)
        except (IOError, ValueError, requests.exceptions.Timeout) as err:
            print('Error:', doi, 'could not be fetched:', err)
            return
        try:
            old = get_pmid(db, new['pmid'])
            if not old: raise KeyError
        except KeyError:
            with PublicationSaver(new, db=db, account=ACCOUNT) as saver:
                labels = saver.get('labels', {}).copy()
                labels[label] = qualifier
                saver['labels'] = labels
            print(doi, 'fetched')
        else:
            with PublicationSaver(old, db=db, account=ACCOUNT) as saver:
                saver['doi'] = doi
                labels = saver.get('labels', {}).copy()
                labels[label] = qualifier
                saver['labels'] = labels
            print(doi, 'set for existing pmid)')

def fetch_bulk(db, filename):
    with open(filename, 'rb') as infile:
        reader = csv.reader(infile)
        reader.next()           # Skip header
        rows = list(reader)
        print(len(rows), 'records in CSV file')
        for row in rows:
            if row[0]:
                fetch_pmid(db, row[0], row[2], row[3])
            elif row[1]:
                fetch_doi(db, row[1], row[2], row[3])


if __name__ == '__main__':
    import sys
    parser = utils.get_command_line_parser(
        'Fetch publications in bulk from CSV file.')
    parser.add_argument('-f', '--csvfile',
                      action='store', dest='csvfile',
                      metavar='CSVFILE', help='path of CSV file')
    args = parser.parse_args()
    utils.load_settings(filepath=args.settings)
    if not args.csvfile:
        sys.exit('Error: no CSV file given')
    db = utils.get_db()
    fetch_bulk(db, args.csvfile)
