"""Trawl PubMed for publications given a CSV file containing authors.
Produces a CSV file containing the aggregated publications references.

Origin: https://github.com/pekrau/Publications/blob/master/publications/scripts/trawl_pubmed.py

NOTE: This is a stand-alone script without any external dependencies,
except for the third-party Python package 'requests'. In particular,
the pubmed module located elsewhere in this package has been inlined here.
This makes it easy to just use this script without having to download
the entire package.

PubMed is searched for a combination of author name, author affiliation
and year of publication, in order to reduce the number of false positive
hits.

All publications for an author are recorded in a file in a subdirectory
'publ{year}' (year being the year set below), which is created if 
it does not exist.

A directory 'pubmed{year}' is also created, which will hold all XML files
fetched from PubMed. This is used as a cache to reduce the network traffic.

The script can be stopped and restarted; it will skip authors which already
have an output file in the subdirectory 'publ{year}'. If you wish to rerun
the search for a specific author, just delete that file in the subdirectory
and rerun this script.

When all authors have been processed, an aggregated file
'all_publ{year}.csv' will be created in the same directory as this script.

Input files:

accounts.csv
  CSV file of author names, as output from OrderPortal. The email address
  is used for the output file (see below). The last name and initials of
  the first names are used for the PubMed search. The university i

universities.csv
  CSV file of university abbreviations.

Output files:

pubmed{year}/*.xml
  XML PubMed entry file; cache to avoid re-getting.

publ{year}/{author-email}.csv
  CSV file of publications found for author.

all_publ{year}.csv
  Aggregated CSV of all publications.
"""

from __future__ import print_function

from collections import OrderedDict
import csv
import os
import os.path
import time
import unicodedata
import xml.etree.ElementTree

# Third-party module available through pip
# http://docs.python-requests.org/en/master/
import requests

YEAR = '2017'
PUBL_DIR = 'publ' + YEAR
PUBMED_DIR = 'pubmed' + YEAR

# Accounts (authors) CSV file, as output from OrderPortal
ACCOUNTS_FILENAME = 'accounts.csv'
EMAIL_COL = 0
LASTNAME_COL = 1
FIRSTNAME_COL = 2
UNIVERSITY_COL = 6

UNIVERSITIES_FILENAME = 'universities.csv'

DELAY = 3.0
TIMEOUT = 10.0

PUBMED_URL = 'https://www.ncbi.nlm.nih.gov/pubmed/'
PUBMED_FETCH_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&rettype=abstract&id=%s'
PUBMED_SEARCH_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmax=%s&term=%s'
MONTHS = dict(jan=1, feb=2, mar=3, apr=4, may=5, jun=6,
              jul=7, aug=8, sep=9, oct=10, nov=11, dec=12)

# Output to CSV file
HEADER_ROW = ['Authors',
              'Title',
              'Journal',
              'Volume',
              'Issue',
              'Pages',
              'Published',
              'PMID',
              'DOI',
              'PubMed URL']
MAX_AUTHORS = 10

def get_accounts(filename=ACCOUNTS_FILENAME):
    "Read accounts CSV file; list of dicts lastname, firstname, university."
    with open(filename, 'rb') as infile:
        reader = csv.reader(infile)
        # Skip 2 header rows
        reader.next()
        reader.next()
        result = []
        for row in reader:
            result.append(dict(email=row[EMAIL_COL],
                               lastname=row[LASTNAME_COL],
                               firstname=row[FIRSTNAME_COL],
                               university=row[UNIVERSITY_COL]))
        return result

def get_universities(filename=UNIVERSITIES_FILENAME):
    "Read universities CSV file; lookup key=abbreviation, values=names."
    with open(filename, 'rb') as infile:
        reader = csv.reader(infile)
        # Skip 1 header row
        reader.next()
        universities = {}
        for row in reader:
            universities[row[0].upper()] = [n for n in row[1:] if n]
        return universities

def create_dir(name):
    if os.path.exists(name):
        if not os.path.isdir(name):
            raise ValueError("%s exists, but is not a directory" % name)
    else:
        os.mkdir(name)

def search_pubmed(accounts, universities, year=YEAR, verbose=True):
    """Find publications in PubMed for each account.
    Fetch the PubMed entries as XML files.
    Output the publications as CSV for each author.
    """
    for account in accounts:
        outfilename = os.path.join(PUBL_DIR, "%s.csv" % account['email'])
        if os.path.exists(outfilename): continue

        name = [account['lastname']]
        initials = ''.join([n[0] for n in account['firstname'].split()])
        if initials:
            name.append(initials)
        name = ' '.join(name)
        try:
            unis = universities[account['university'].upper()]
        except KeyError:
            if account['university']:
                unis = [account['university']]
            else:
                unis = []
        pmids = set()
        kwargs = dict(author=name, published=year)
        if unis:
            for uni in unis:
                kwargs['affiliation'] = uni
                pmids.update(search(**kwargs))
        else:
            pmids.update(search(**kwargs))
        if verbose:
            print(name, ':', len(pmids))
        entries = [fetch(pmid) for pmid in pmids]
        with open(outfilename, 'w') as outfile:
            writer = csv.writer(outfile,
                                dialect=csv.excel,
                                quoting=csv.QUOTE_NONNUMERIC)
            writer.writerow(HEADER_ROW)
            for entry in entries:
                authors = [u"%s %s" % (a.get('family') or '',
                                       a.get('initials') or '')
                           for a in entry['authors']]
                if len(authors) > MAX_AUTHORS:
                    authors = ', '.join(authors[:MAX_AUTHORS-1]) + \
                            '...' + authors[-1]
                else:
                    authors = ', '.join(authors)
                writer.writerow(row_to_utf8(
                    [authors,
                     entry['title'],
                     entry['journal']['title'],
                     entry['journal'].get('volume') or '',
                     entry['journal'].get('issue') or '',
                     entry['journal'].get('pages') or '',
                     entry['published'],
                     entry['pmid'],
                     entry['doi'],
                     PUBMED_URL + entry['pmid']]))

def aggregate(verbose=True):
    "Aggregate all records from files in the publications directory."
    pmids = set()
    filename = "publ%s.csv" % YEAR
    count = 0
    unique = 0
    with open(filename, 'w') as outfile:
        writer = csv.writer(outfile,
                            dialect=csv.excel,
                            quoting=csv.QUOTE_NONNUMERIC)
        writer.writerow(HEADER_ROW)
        for dirpath, dirnames, filenames in os.walk(PUBL_DIR):
            for filename in filenames:
                with open(os.path.join(dirpath, filename), 'rb') as infile:
                    reader = csv.reader(infile)
                    # Skip 1 header row
                    reader.next()
                    for row in reader:
                        count += 1
                        if row[7] in pmids: continue
                        writer.writerow(row)
                        pmids.add(row[7])
                        unique += 1
    if verbose:
        print(unique, 'publications,', count, 'total in author files')

def search(author=None, published=None, journal=None, doi=None,
           affiliation=None, title=None, exclude_title=None,
           delay=DELAY, retmax=100):
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
        if delay > 0.0:
            time.sleep(delay)
        response = requests.get(url, timeout=TIMEOUT)
    except (requests.exceptions.ReadTimeout,
            requests.exceptions.ConnectionError) as err:
        raise IOError("timeout %s" % err)
    if response.status_code != 200:
        raise IOError("HTTP status %s, %s " % (response.status_code, url))
    root = xml.etree.ElementTree.fromstring(response.content)
    return [e.text for e in root.findall('IdList/Id')]

def fetch(pmid, dirname=PUBMED_DIR, delay=DELAY):
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
        if delay > 0.0:
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
    result['title']      = get_title(article)
    result['pmid']       = get_pmid(article)
    result['doi']        = None
    result['authors']    = get_authors(article)
    result['journal']    = get_journal(article)
    result['type']       = get_type(article)
    result['published']  = get_published(article)
    result['epublished'] = get_epublished(article)
    result['abstract']   = get_abstract(article)
    result['xrefs']      = []
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
            author[jkey + '_normalized'] = to_ascii(value).lower()
        # For consortia and such, names are a mess. Try to sort out.
        if not author.get('family'):
            try:
                author['family'] = author.pop('given')
            except KeyError:
                value = element.findtext('CollectiveName')
                if not value: continue # Give up.
                value = to_unicode(value)
                author['family'] = value
            author['given'] = ''
            author['initials'] = ''
            author['family_normalized'] = to_ascii(author['family']).lower()
            try:
                author.pop('given_normalized')
            except KeyError:
                pass
            author['given_normalized'] = ''
            author['initials_normalized'] = ''
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
    # Add dummy values, if missing
    if len(date) == 1: date.append(0)
    if len(date) == 2: date.append(0)
    return "%s-%02i-%02i" % tuple(date)

def get_epublished(article):
    "Get the online publication date from the article XML tree, or None."
    date = []
    elem = article.find('MedlineCitation/Article/ArticleDate')
    if elem is not None and elem.get('DateType') == 'Electronic':
        date = get_date(elem)
    if len(date) < 2:
        dates = article.findall('PubmedData/History/PubMedPubDate')
        for status in ['epublish', 'aheadofprint', 'pubmed']:
            for elem in dates:
                if elem.get('PubStatus') == status:
                    date = get_date(elem)
                    break
            if len(date) >= 2: break
    if len(date) == 0:          # No date found
        return None
    # Add dummy values, if missing
    if len(date) == 1: date.append(0)
    if len(date) == 2: date.append(0)
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
    if value:
        return unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    else:
        return ''

def row_to_utf8(row):
    "Convert any unicode to utf-8, and return row."
    for pos, item in enumerate(row):
        if isinstance(item, unicode):
            row[pos] = item.encode('utf-8')
    return row


if __name__ == '__main__':
    accounts = get_accounts()
    print(len(accounts), 'accounts')
    universities = get_universities()
    print(len(universities), 'universities')
    create_dir(PUBL_DIR)
    create_dir(PUBMED_DIR)
    search_pubmed(accounts, universities)
    aggregate()
