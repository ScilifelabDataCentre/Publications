"""Fetch publications in bulk given a CSV file with PMID, DOI,
label and qualifier, as columns 1, 2, 3, and 4, respectively.
If there is no PMID (empty column 1) then there must be a DOI in
column 2.
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

def check_blacklist_pmid(db, pmid):
    "Raise ValueError if the PMID is blacklisted."
    if utils.get_blacklisted(db, pmid):
        raise ValueError("%s is blacklisted!" % pmid)

def check_blacklist_doi(db, doi):
    "Raise ValueError if the DOI is blacklisted."
    if utils.get_blacklisted(db, doi):
        raise ValueError("%s is blacklisted!" % doi)

def check_label(db, label):
    "Raise ValueError if no such label."
    try:
        utils.get_label(db, label)
    except KeyError:
        raise ValueError("label %s does not exist" % label)

def check_qualifier(db, qualifier):
    if qualifier not in settings['SITE_LABEL_QUALIFIERS']:
        raise ValueError("qualifier %s does not exist", qualifier)

def fetch_pmid(db, pmid, label, qualifier):
    """Fetch the publication reference given the PMID.
    Update the existing record, if any.
    Apply the given label and qualifier.
    Raise KeyError if no such PMID.
    """
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
        except (IOError, ValueError, requests.exceptions.Timeout) as error:
            raise KeyError('%s could not be fetched: %s' % (pmid, error))
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
    Raise KeyError if no such DOI.
    """
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
            raise KeyError('%s could not be fetched: %s' % (doi, error))
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
   """"CSV file format:
   PMID, DOI, label and qualifier, as columns 1, 2, 3, and 4, respectively.
   If there is no PMID (empty column 1) then there must be a DOI in
   column 2.
   If any errors are detected before the fetching phase,
   this functions returns without attempting any fetch.
   """
    with open(filename, 'rb') as infile:
        reader = csv.reader(infile)
        reader.next()           # Skip header
        rows = list(reader)
        print(len(rows), 'records in CSV file')
        # Check data in CSV file
        bail = False
        for nrow, row in enumerate(rows):
            try:
                if row[0]:
                    check_pmid(db, row[0])
                elif row[1]:
                    check_doi(db, row[1])
                else:
                    raise ValueError('no PMID or DOI')
                check_label(db, row[2])
                check_qualifier(db, row[3])
            except ValueError as error:
                print('Error row', nrow, str(error))
                bail = True
        if bail: return
        # Fetch publications
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
