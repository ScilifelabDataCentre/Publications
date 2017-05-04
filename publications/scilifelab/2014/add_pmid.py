"""Add PMID to column 12 of the CSV file if none defined.
Iterate over file versions."""

from __future__ import print_function

import csv
import sys
import time

from publications import crossref
from publications import pubmed
from publications import utils

INFILENAME = 'publikationer faciliteter 2010-2014 pmid v1.csv'
OUTFILENAME = 'publikationer faciliteter 2010-2014 pmid v2.csv'

AUTHOR_POS = 3
TITLE_POS = 4
YEAR_POS = 9
PMID_POS = 12
DELAY = 1.0

with open(INFILENAME, 'rb') as infile:
    reader = csv.reader(infile)
    header = reader.next()
    records = list(reader)

lookup = dict()
for record in records:
    try:
        pmid = record[PMID_POS].strip()
    except IndexError:
        pmid = None
    if pmid:
        lookup[record[TITLE_POS]] = pmid
    
with open(OUTFILENAME, 'wb') as outfile:
    writer = csv.writer(outfile)
    writer.writerow(header)

    for record in records:
        if not record[TITLE_POS].strip(): continue
        title = record[TITLE_POS]
        pmid = lookup.get(title)
        if not pmid:
            time.sleep(DELAY)
            print(title)
            title = title.rstrip('.').strip()
            year = record[YEAR_POS]
            try:
                pmids = pubmed.search(title=title, published=year)
                if len(pmids) == 1:
                    pmid = pmids[0]
                else:
                    author = utils.to_ascii(record[AUTHOR_POS])
                    author = author.replace('and', ' ')
                    author = author.replace('.', '')
                    author = ' '.join([' '.join([p for p in a.split()
                                                 if len(p) > 2]) 
                                       for a in author.split(',')[:6]])
                    year = record[YEAR_POS]
                    print(author, year)
                    pmids = pubmed.search(author=author, published=year)
            except IOError, msg:
                print('Error:', msg)
                pmids = []
            if len(pmids) == 1:
                pmid = pmids[0]
            print(pmid)
        if pmid:
            try:
                record[PMID_POS] = pmid
            except IndexError:
                record.append(pmid)
        writer.writerow(record)
        outfile.flush()
