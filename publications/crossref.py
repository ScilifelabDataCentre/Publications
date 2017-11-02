"Crossref interface."

from __future__ import print_function

from collections import OrderedDict
import json
import time
import unicodedata

import requests

CROSSREF_FETCH_URL = 'http://api.crossref.org/works/%s'

TIMEOUT = 5.0


def fetch(doi, debug=False, delay=None):
    "Fetch publication JSON data from Crossref and parse into a dictionary."
    url = CROSSREF_FETCH_URL % doi
    if delay:
        time.sleep(delay)
    response = requests.get(url, timeout=TIMEOUT)
    if response.status_code != 200:
        raise IOError("HTTP status %s, %s " % (response.status_code, url))
    if debug:
        print(json.dumps(response.json(), indent=2))
    return parse(response.json())

def parse(data):
    "Parse JSON data for a publication into a dictionary."
    result = OrderedDict()
    result['title']      = get_title(data)
    result['doi']        = get_doi(data)
    result['pmid']       = get_pmid(data)
    result['authors']    = get_authors(data)
    result['journal']    = get_journal(data)
    result['type']       = get_type(data)
    result['published']  = get_published(data)
    result['epublished'] = get_epublished(data)
    result['abstract']   = get_abstract(data)
    result['xrefs']      = get_xrefs(data)
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
    for item in data['message'].get('author', []):
        author = OrderedDict()
        author['family'] = item.get('family')
        author['family_normalized'] = to_ascii(author['family']).lower()
        # Remove dots and dashes
        given = item.get('given', '').replace('.', ' ').replace('-', ' ')
        # Replace weird blank characters
        author['given'] = ' '.join(given.split())
        author['given_normalized'] = to_ascii(author['given']).lower()
        author['initials'] = ''.join([n[0] for n in given.split()])
        author['initials_normalized'] = to_ascii(author['initials']).lower()
        try:
            author['orcid'] = item['ORCID']
        except KeyError:
            pass
        result.append(author)
    return result

def get_journal(data):
    "Get the journal data from the article JSON."
    result = OrderedDict()
    try:
        result['title'] = ' '.join(data['message']['short-container-title'])
    except KeyError:
        result['title'] = ' '.join(data['message']['container-title'])
    try:
        result['issn'] = data['message']['ISSN'][0]
    except (KeyError, IndexError):
        result['issn'] = None
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
    "Get the print publication date from the article JSON."
    # Try in order: print, issued, created
    for key in ['published-print', 'issued', 'created']:
        try:
            item = data['message'][key]
        except KeyError:
            pass
        else:
            break
    parts = [int(i) for i in item['date-parts'][0]]
    # Add dummy values, if missing
    if len(parts) == 1: parts.append(0)
    if len(parts) == 2: parts.append(0)
    return "%s-%02i-%02i" % tuple(parts)

def get_epublished(data):
    "Get the online publication date from the article JSON, or None."
    # Try in order: online, issued
    for key in ['published-online', 'issued']:
        try:
            item = data['message'][key]
        except KeyError:
            pass
        else:
            break
    else:
        return None
    parts = [int(i) for i in item['date-parts'][0]]
    # Add dummy values, if missing
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
    if value:
        return unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    else:
        return ''


def test_fetch():
    "Fetch a specific article."
    key = '10.1016/j.cell.2015.12.018'
    result = fetch(key)
    assert result['doi'] == key


if __name__ == '__main__':
    doi = '10.1126/science.1260419'
    url = CROSSREF_FETCH_URL % doi
    response = requests.get(url, timeout=TIMEOUT)
    if response.status_code != 200:
        raise IOError("HTTP status %s, %s " % (response.status_code, url))
    with open('data/%s' % doi.replace('/', '_'), 'w') as outfile:
        outfile.write(json.dumps(response.json(), indent=2))
