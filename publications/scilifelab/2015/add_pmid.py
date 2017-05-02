"Add PMID to column 14 of the CSV file if none defined."

from __future__ import print_function

import csv
import time

from publications import pubmed

INFILENAME = 'Publikationer Faciliteten anv 2015.csv'
OUTFILENAME = 'Publikationer Faciliteten anv 2015 pmids.csv'
AUTHOR_POS = 3
TITLE_POS = 4
YEAR_POS = 9
PMID_POS = 14
DELAY = 1.0
AUTHOR_MAX_LENGTH = 200


def reformat_authors(authors, max_authors=5):
    result = []
    authors = authors.split(',')
    authors = authors[:max_authors]
    for author in authors:
        parts = author.replace('.', ' ').strip().split()
        result.append("%s %s" % (parts[-1], ''.join(parts[:-1])))
    return ' '.join(result)

# Already found PMIDs
found = {'Comprehensive genomic profiles of small cell lung cancer': '26168399',
         'The human cardiac and skeletal muscle proteomes defined by transcriptomics and antibody-based profiling': '26109061',
         'Whole-genome Linkage Analysis and Sequence Analysis of Candidate Loci in Familial Breast Cancer': '26026075'}
try:
    with open(OUTFILENAME, 'rb') as infile:
        reader = csv.reader(infile)
        reader.next()
        for record in reader:
            try:
                pmid = record[PMID_POS].strip()
            except IndexError:
                pass
            else:
                if pmid:
                    found[record[TITLE_POS]] = pmid
    print(len(found), 'PMIDs already found')
except IOError:
    pass


with open(OUTFILENAME, 'wb') as outfile:
    writer = csv.writer(outfile)

    with open(INFILENAME, 'rb') as infile:
        reader = csv.reader(infile)
        header = reader.next()
        writer.writerow(header)
        for record in reader:
            pmid = found.get(record[TITLE_POS])
            if not pmid:
                print(record[TITLE_POS])
                pmids = pubmed.search(title=record[TITLE_POS])
                if len(pmids) != 1:
                    pmids = pubmed.search(author=reformat_authors(record[AUTHOR_POS]),
                                          published=record[YEAR_POS])
                print(pmids)
                if len(pmids) == 1:
                    pmid = pmids.pop()
                else:
                    pmid = "[%s]" % len(pmids)
            try:
                record[PMID_POS] = pmid
            except IndexError:
                record.append(pmid)
            record[AUTHOR_POS] = record[AUTHOR_POS][:AUTHOR_MAX_LENGTH]
            writer.writerow(record)
