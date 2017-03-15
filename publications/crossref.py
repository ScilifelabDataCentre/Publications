"Publications: Crossref interface."

from __future__ import print_function

from collections import OrderedDict
import json
import unicodedata

import requests

CROSSREF_FETCH_URL = 'http://api.crossref.org/works/%s'

TIMEOUT = 5.0


session = requests.Session()

def fetch(doi):
    "Fetch publication JSON data from Crossref and parse into a dictionary."
    url = CROSSREF_FETCH_URL % doi
    response = session.get(url, timeout=TIMEOUT)
    if response.status_code != 200:
        raise IOError("HTTP status %s, %s " % (response.status_code, url))
    return parse(response.json())

def parse(data):
    "Parse JSON data for a publication into a dictionary."
    result = OrderedDict()
    result['title']     = get_title(data)
    result['doi']       = get_doi(data)
    result['pmid']      = get_pmid(data)
    result['authors']   = get_authors(data)
    result['journal']   = get_journal(data)
    result['type']      = get_type(data)
    result['published'] = get_published(data)
    result['abstract']  = get_abstract(data)
    result['xrefs']     = get_xrefs(data)
    return result

def get_title(data):
    "Get the title from the article JSON."
    try:
        return ' '.join(data['message']['title'])
    except KeyError:
        for item in data['message']['assertion']:
            if item['name'] == 'articletitle':
                return item['value']

def get_doi(data):
    "Get the DOI from the article JSON."
    return data['message']['DOI']

def get_pmid(data):
    "Get the PMID from the article JSON; not present."
    return None

def get_authors(data):
    "Get the list of authors from the article JSON."
    result = []
    for item in data['message']['author']:
        author = OrderedDict()
        author['family'] = item.get('family')
        author['family_normalized'] = to_ascii(author['family'])
        # Remove dots and replace weird blank characters
        given = item['given'].replace('.', ' ')
        author['given'] = ' '.join(given.split())
        author['given_normalized'] = to_ascii(author['given'])
        author['initials'] = ''.join([n[0] for n in given.split()])
        author['initials_normalized'] = to_ascii(author['initials'])
        try:
            author['orcid'] = item['ORCID']
        except KeyError:
            pass
        result.append(author)
    return result

def get_journal(data):
    "Get the journal data from the article JSON."
    result = OrderedDict()
    result['title'] = ' '.join(data['message']['container-title'])
    try:
        result['issn'] = data['message']['ISSN'][0]
    except (KeyError, IndexError):
        result['issn'] = None
    try:
        result['abbreviation'] = ' '.join(data['message']['short-container-title'])
    except KeyError:
        result['abbreviation'] = None
    result['volume'] = data['message'].get('volume')
    result['issue'] = data['message'].get('issue')
    result['pages'] = data['message'].get('page')
    return result

def get_type(data):
    "Get the type from the article JSON."
    try:
        return data['message'].get('type')
    except KeyError:
        return None

def get_published(data):
    "Get the publication date from the article JSON."
    try:
        item = data['message']['published-print']
    except KeyError:
        try:
            item = data['message']['issued']
        except KeyError:
            item = data['message']['created']
    parts = [int(i) for i in item['date-parts'][0]]
    if len(parts) == 1: parts.append(0)
    if len(parts) == 2: parts.append(0)
    return "%s-%02i-%02i" % tuple(parts)

def get_abstract(data):
    "Get the abstract from the article JSON; not present."
    return None

def get_xrefs(data):
    "Get the list of cross-references from the article JSON; not present."
    return []

def to_ascii(value):
    "Convert any non-ASCII character to its closest equivalent."
    return unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')


def test_fetch():
    "Fetch a specific article."
    key = '10.1016/j.cell.2015.12.018'
    result = fetch(key)
    assert result['doi'] == key
