"PubMed interface."

from __future__ import print_function

from collections import OrderedDict
import os
import time
import unicodedata
import xml.etree.ElementTree

import requests

PUBMED_FETCH_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&rettype=abstract&id=%s'

PUBMED_SEARCH_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmax=%s&term=%s'

TIMEOUT = 5.0

MONTHS = dict(jan=1, feb=2, mar=3, apr=4, may=5, jun=6,
              jul=7, aug=8, sep=9, oct=10, nov=11, dec=12)


def search(author=None, published=None, journal=None, doi=None,
           affiliation=None, title=None, exclude_title=None,
           retmax=100):
    "Get list of PMIDs for PubMed hits given the data."
    parts = []
    if author:
        parts.append("%s[AU]" % to_ascii(to_unicode(author)))
    if published:
        parts.append("%s[DP]" % published)
    if journal:
        parts.append("%s[TA]" % journal)
    if doi:
        parts.append("%s[LID]" % doi)
    if affiliation:
        parts.append("%s[AD]" % to_ascii(to_unicode(affiliation)))
    if title:
        parts.append("%s[TI]" % to_ascii(to_unicode(title)))
    query = ' AND '.join(parts)
    if exclude_title:
        query += " NOT %s[TI]" % to_ascii(to_unicode(exclude_title))
    url = PUBMED_SEARCH_URL % (retmax, query)
    try:
        response = requests.get(url, timeout=TIMEOUT)
    except (requests.exceptions.ReadTimeout,
            requests.exceptions.ConnectionError):
        raise IOError('timeout')
    if response.status_code != 200:
        raise IOError("HTTP status %s, %s " % (response.status_code, url))
    root = xml.etree.ElementTree.fromstring(response.content)
    return [e.text for e in root.findall('IdList/Id')]

def fetch(pmid, dirname=None, delay=None):
    """Fetch publication XML from PubMed and parse into a dictionary.
    Use the file cache directory if given.
    Delay the HTTP request if positive value (seconds).
    """
    filename = pmid + '.xml'
    content = None
    if dirname:
        try:
            with open(os.path.join(dirname, filename)) as infile:
                content = infile.read()
        except IOError:
            pass
    if not content:
        url = PUBMED_FETCH_URL % pmid
        if delay:
            time.sleep(delay)
        response = requests.get(url, timeout=TIMEOUT)
        if response.status_code != 200:
            raise IOError("HTTP status %s, %s " % (response.status_code, url))
        content = response.content
        if dirname:
            with open(os.path.join(dirname, filename), 'w') as outfile:
                outfile.write(content)
    return parse(content)

def parse(data):
    "Parse XML text data for a publication into a dictionary."
    result = OrderedDict()
    tree = xml.etree.ElementTree.fromstring(data)
    article = get_element(tree, 'PubmedArticle')
    result['title']     = get_title(article)
    result['pmid']      = get_pmid(article)
    result['doi']       = None
    result['authors']   = get_authors(article)
    result['journal']   = get_journal(article)
    result['type']      = get_type(article)
    result['published'] = get_published(article)
    result['abstract']  = get_abstract(article)
    result['xrefs']     = []
    # Remove PMID from xrefs; get and remove DOI
    for xref in get_xrefs(article):
        if xref['db'] == 'doi':
            result['doi'] = xref['key']
        elif xref['db'] == 'pubmed':
            pass
        else:
            result['xrefs'].append(xref)
    return result

def get_title(article):
    "Get the title from the article XML tree."
    element = get_element(article, 'MedlineCitation/Article')
    return element.findtext('ArticleTitle')

def get_pmid(article):
    "Get the PMID from the article XML tree."
    return article.findtext('MedlineCitation/PMID')

def get_authors(article):
    "Get the list of authors from the article XML tree."
    element = get_element(article, 'MedlineCitation/Article')
    authorlist = element.find('AuthorList')
    result = []
    existing = set()                # Handle pathological multi-mention.
    for element in authorlist.findall('Author'):
        author = OrderedDict()
        for jkey, xkey in [('family', 'LastName'),
                           ('given', 'ForeName'),
                           ('initials', 'Initials')]:
            value = element.findtext(xkey)
            if not value: continue
            value = to_unicode(value)
            author[jkey] = value
            author[jkey + '_normalized'] = to_ascii(value)
        # For consortia and such, names are a mess. Try to sort out.
        if not author.get('family'):
            try:
                author['family'] = author.pop('given')
            except KeyError:
                value = element.findtext('CollectiveName')
                if not value: continue # Give up.
                value = to_unicode(value)
                author['family'] = value
            author['given'] = None
            author['initials'] = None
            author['family_normalized'] = to_ascii(author['family'])
            try:
                author.pop('given_normalized')
            except KeyError:
                pass
            author['given_normalized'] = None
            author['initials_normalized'] = None
        if author:
            try:                    # Give up if this doesn't work
                key = "%(family)s %(given)s" % author
                if key not in existing:
                    result.append(author)
                    existing.add(key)
            except KeyError:
                pass
    return result

def get_journal(article):
    "Get the journal data from the article XML tree."
    element = get_element(article, 'MedlineCitation/Article/Journal')
    result = OrderedDict()
    if element is not None:
        result['title'] = element.findtext('ISOAbbreviation')
        if not result['title']:
            result['title'] = element.findtext('Title')
        result['issn'] = element.findtext('ISSN')
        issue = element.find('JournalIssue')
        if issue is not None:
            result['volume'] = issue.findtext('Volume')
            result['issue'] = issue.findtext('Issue')
    element = article.find('MedlineCitation/Article/Pagination/MedlinePgn')
    if element is not None:
        pages = element.text
        if pages:
            pages = pages.split('-')
            if len(pages) == 2:         # Complete page numbers!
                diff = len(pages[0]) - len(pages[1])
                if diff > 0:
                    pages[1] = pages[0][0:diff] + pages[1]
            pages = '-'.join(pages)
        result['pages'] = pages
    return result

def get_type(article):
    "Get the type from the article XML tree."
    element = get_element(article, 'MedlineCitation/Article/PublicationTypeList/PublicationType')
    if element is not None:
        return element.text.lower()
    else:
        return None

def get_published(article):
    "Get the publication date from the article XML tree."
    elem = article.find('MedlineCitation/Article/Journal/JournalIssue/PubDate')
    date = []
    if elem is not None:
        date = get_date(elem)
    if len(date) < 2:               # Fallback 1: ArticleDate
        elem = article.find('MedlineCitation/Article/ArticleDate')
        if elem is not None:
            date = get_date(elem)
    if len(date) < 2:               # Fallback 2: PubMedPubDate
        dates = article.findall('PubmedData/History/PubMedPubDate')
        for status in ['epublish', 'aheadofprint', 'pubmed']:
            for elem in dates:
                if elem.get('PubStatus') == status:
                    date = get_date(elem)
                    break
            if len(date) >= 2: break
    if len(date) == 0:              # Fallback 3: today's year
        d = time.localtime()
        date = [d.tm_year, 0, 0]
    elif len(date) == 1:            # Add dummy month
        date.append(0)
    elif len(date) == 2:            # Add dummy day
        date.append(0)
    return "%s-%02i-%02i" % tuple(date)

def get_abstract(article):
    "Get the abstract from the article XML tree."
    try:
        element = get_element(article, 'MedlineCitation/Article/Abstract')
    except ValueError:
        return None
    else:
        return '\n\n'.join([e.text for e in
                            element.findall('AbstractText')])

def get_xrefs(article):
    "Get the list of cross-references from the article XML tree."
    result = []
    for elem in article.findall('PubmedData/ArticleIdList/ArticleId'):
        result.append(dict(db=elem.get('IdType'), key=elem.text))
    for elem in article.findall('MedlineCitation/Article/DataBankList/DataBank'):
        db = elem.findtext('DataBankName')
        if not db: continue
        for elem2 in elem.findall('AccessionNumberList/AccessionNumber'):
            result.append(dict(db=db, key=elem2.text))
    return result

def get_element(tree, key):
    element = tree.find(key)
    if element is None: raise ValueError("could not find %s element" % key)
    return element

def get_date(element):
    "Get the [year, month, day] from the element."
    year = element.findtext('Year')
    if not year:
        return []
    result = [int(year)]
    month = element.findtext('Month')
    if not month:
        return result
    try:
        month = int(MONTHS.get(month.lower()[:3], month))
    except (TypeError, ValueError):
        return result
    else:
        result.append(month)
    day = element.findtext('Day')
    try:
        day = int(day)
    except (TypeError, ValueError):
        day = 0
    result.append(day)
    return result

def to_unicode(value):
    "Convert to unicode using UTF-8 if not already done."
    if isinstance(value, unicode):
        return value
    else:
        return unicode(value, 'utf-8')

def to_ascii(value):
    "Convert any non-ASCII character to its closest equivalent."
    return unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')


def test_fetch():
    "Fetch a specific article."
    key = '8142349'
    result = fetch(key)
    assert result['pmid'] == key
    
def test_search():
    "Search for a specific set of PMIDs."
    result = search(author='Kraulis PJ', published='1994')
    assert set(result) == set(['7525970', '8142349'])
