"""Add PMID to column 12 of the CSV file if none defined.
Iterate over file versions."""

from __future__ import print_function

import csv
import sys
import time

from publications import crossref
from publications import pubmed

LOOKUPFILENAME = 'Facility publications 2016 pmids v2.csv'

INFILENAME = '10. Facility publications all 1 & 2 (inkl JIF).csv'
OUTFILENAME = 'Facility publications 2016 pmids v3.csv'

DOI_POS = 3
TITLE_POS = 9
PMID_POS = 12
DELAY = 1.0

lookup = dict()
try:
    with open(LOOKUPFILENAME) as infile:
        reader = csv.reader(infile)
        reader.next()
        for record in reader:
            try:
                pmid = record[PMID_POS].strip()
            except IndexError:
                pass
            else:
                if pmid:
                    lookup[record[TITLE_POS]] = pmid
except IOError:
    pass

def format_authors(authors):
    result = []
    for author in authors:
        result.append("%s %s" % (author['family_normalized'],
                                 author['initials_normalized']))
    return ', '.join(result)

with open(INFILENAME, 'rb') as infile:
    reader = csv.reader(infile)
    header = reader.next()
    records = list(reader)

with open(OUTFILENAME, 'wb') as outfile:
    writer = csv.writer(outfile)
    writer.writerow(header)

    for record in records:
        doi = record[DOI_POS].split(':')[-1].strip()
        print(doi)
        pmid = lookup.get(record[TITLE_POS])
        if not pmid:
            time.sleep(DELAY)
            try:
                data = crossref.fetch(doi)
            except IOError, msg:
                print("Error %s" % msg)
            else:
                pmid = data['pmid']
                if not pmid:
                    pmids = pubmed.search(title=record[TITLE_POS])
                    if len(pmids) == 1:
                        pmid = pmids[0]
                    else:
                        author = format_authors(data['authors'][:4])
                        year = data['published'].split('-')[0]
                        try:
                            pmids = pubmed.search(author=author,
                                                  published=year)
                        except IOError, msg:
                            print('Error:', msg)
                            pmids = []
                        if len(pmids) == 1:
                            pmid = pmids[0]
                print(pmid)
        try:
            record[PMID_POS] = pmid
        except IndexError:
            record.append(pmid)
        writer.writerow(record)
        outfile.flush()
