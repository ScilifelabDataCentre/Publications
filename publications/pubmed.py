"Publications: PubMed interface."

from __future__ import print_function

from collections import OrderedDict
import time
import unicodedata
import xml.etree.ElementTree

import requests

PUBMED_FETCH_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&rettype=abstract&id=%s'

PUBMED_SEARCH_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmax=%s&term=%s'

MONTHS = dict(jan=1, feb=2, mar=3, apr=4, may=5, jun=6,
              jul=7, aug=8, sep=9, oct=10, nov=11, dec=12)


session = requests.Session()

def search(author=None, published=None, journal=None, 
           affiliation=None, words=None, retmax=100):
    "Get list of PMIDs for PubMed hits given the data."
    parts = []
    if author:
        parts.append("%s[Author]" % to_ascii(to_unicode(author)))
    if published:
        parts.append("%s[PDAT]" % published)
    if journal:
        parts.append("%s[Journal]" % journal)
    if affiliation:
        parts.append("%s[Affiliation]" % to_ascii(to_unicode(affiliation)))
    if words:
        parts.append(words.replace(' ', '+'))
    url = PUBMED_SEARCH_URL % (retmax, ' AND '.join(parts))
    response = session.get(url)
    if response.status_code != 200:
        raise IOError("HTTP status %s, %s " % (response.status_code, url))
    root = xml.etree.ElementTree.fromstring(response.content)
    return [e.text for e in root.findall('IdList/Id')]

def fetch(pmid):
    "Fetch publication XML from PubMed and parse into a dictionary."
    url = PUBMED_FETCH_URL % pmid
    response = session.get(url)
    if response.status_code != 200:
        raise IOError("HTTP status %s, %s " % (response.status_code, url))
    return parse(response.content)

def parse(xmldata):
    "Parse XML data for a publication into a dictionary."
    result = OrderedDict()
    tree = xml.etree.ElementTree.fromstring(xmldata)
    article = get_element(tree, 'PubmedArticle')
    result['pmid']      = get_pmid(article)
    result['doi']       = None
    result['title']     = get_title(article)
    result['authors']   = get_authors(article)
    result['journal']   = get_journal(article)
    result['type']      = get_type(article)
    result['published'] = get_published(article)
    result['abstract']  = get_abstract(article)
    result['xrefs']     = get_xrefs(article)
    for xref in result['xrefs']:
        if xref['db'] == 'doi':
            result['doi'] = xref['key']
            break
    return result

def get_pmid(article):
    "Get the PMID from the article XML tree."
    return article.findtext('MedlineCitation/PMID')

def get_title(article):
    "Get the title from the article XML tree."
    element = get_element(article, 'MedlineCitation/Article')
    return element.findtext('ArticleTitle') or '[no title}'

def get_authors(article):
    "Get the list of authors from the article XML tree."
    element = get_element(article, 'MedlineCitation/Article')
    authorlist = element.find('AuthorList')
    result = []
    existing = set()                # Handle pathological multi-mention.
    for element in authorlist.findall('Author'):
        author = dict()
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
    result = dict()
    if element is not None:
        result['issn'] = element.findtext('ISSN')
        result['title'] = element.findtext('Title')
        result['abbreviation'] = element.findtext('ISOAbbreviation')
        issue = element.find('JournalIssue')
        if issue is not None:
            result['volume'] = issue.findtext('Volume')
            result['issue'] = issue.findtext('Issue')
    element = article.find('Pagination/MedlinePgn')
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
    if len(date) == 0:              # Fallback 3: today's year and month
        d = time.localtime()
        date = [d.tm_year, d.tm_mon, 0]
    elif len(date) == 1:            # Add today's month
        d = time.localtime()
        date = [date[0], d.tm_mon, 0]
    elif len(date) == 2:            # Add dummy day
        date.append(0)
    return "%s-%02i-%02i" % tuple(date)

def get_abstract(article):
    "Get the abstract from the article XML tree."
    element = get_element(article, 'MedlineCitation/Article')
    return '\n\n'.join([e.text for e in
                        element.findall('Abstract/AbstractText')])

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

def to_unicode(value):
    "Convert to unicode using UTF-8 if not already done."
    if isinstance(value, unicode):
        return value
    else:
        return unicode(value, 'utf-8')

def to_ascii(value):
    "Convert any non-ASCII character to its closest equivalent."
    return unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')

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


def test_fetch():
    "Fetch a specific article."
    key = '8142349'
    result = fetch(key)
    assert result['pmid'] == key
    
def test_search():
    "Search for a specific set of PMIDs."
    result = search(author='Kraulis PJ', published='1994')
    assert set(result) == set(['7525970', '8142349'])


if __name__ == '__main__':
    test_fetch()
    test_search()
