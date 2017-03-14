"Publications: Add a publication to the database."

from __future__ import print_function

import json
import os
import sys
import time

import requests

from publications import constants
from publications import utils
from publications.publication import PublicationSaver


CACHE_DIR = 'data'
CROSSREF_URL = 'http://api.crossref.org/works/%s'
PUBMED_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json&rettype=abstract&id=%s'

delay = 2.0
latest = None
session = requests.Session()

def get_args():
    parser = utils.get_command_line_parser(description='Add a publication.')
    parser.add_option('-d', '--delay',
                      action='store', dest='delay', type='float', default=delay,
                      help='Delay between web service fetches (default 2.0 sec).')
    return parser.parse_args()

def get_filepath(identifier):
    if CACHE_DIR:
        return os.path.join(CACHE_DIR,
                            "{}.json".format(identifier.replace('/', '_')))

def get_cached_document(identifier):
    filepath = get_filepath(identifier)
    if os.path.exists(filepath):
        with open(filepath, mode='r') as infile:
            return json.load(infile)

def get_document(base_url, identifier):
    global latest
    url = base_url % identifier
    if latest:
        pause = time.time() - (latest + delay)
        if pause > 0.0:
            time.sleep(pause)
    response = session.get(url)
    latest = time.time()
    if response.status_code != 200:
        raise ValueError("could not fetch %s" % url)
    else:
        result = response.json()
        if CACHE_DIR:
            filepath = get_filepath(identifier)
            if filepath:
                with open(filepath, mode='w') as outfile:
                    json.dump(result, outfile, indent=2)
    return result

def get_pmid_document(pmid):
    return get_document(PUBMED_URL, pmid)

def get_doi_document(doi):
    return get_document(CROSSREF_URL, doi)

def add_publication(identifier):
    with PublicationSaver(db=utils.get_db()) as saver:
        if constants.PMID_RX.match(identifier):
            pass
        else:
            pass
    print('Added publication', identifier, ':', )


if __name__ == '__main__':
    (options, args) = get_args()
    utils.load_settings(filepath=options.settings)
    delay = max(0.0, options.delay)
    print(os.getcwd())
    for identifier in args:
        if constants.PMID_RX.match(identifier):
            get_pmid_document(identifier)
        else:
            get_doi_document(identifier)
