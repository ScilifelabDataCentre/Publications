"""Process publications from the Leiden 2018 spreadsheet.
- Search for PMID from DOI using PubMed
- Write out CSV file of mapping DOI->PMID.
"""

import csv
import time

import requests

from publications import pubmed


PAUSE = 3.0
ACTOR_COL = 1
DOI_COL = 9

def process_leiden_2018(csvfilename):
    pmids_done = set()
    try:
        with open('pmids_lookup.csv', 'rb') as infile:
            reader = csv.reader(infile)
            next(reader)
            for row in reader:
                pmids_done.add(row[0])
    except IOError:
        pass
    counts = {}
    rows = []
    with open(csvfilename, 'rb') as infile:
        reader = csv.reader(infile)
        next(reader)
        for row in reader:
            counts[row[ACTOR_COL]] = counts.get(row[ACTOR_COL], 0) + 1
            if row[ACTOR_COL] == 'SciLifeLab':
                rows.append(row)
        print(counts)
        print(len(rows))
    for pos, row in enumerate(rows):
        doi = row[DOI_COL]
        if doi in pmids_done: continue
        print(doi)
        pmids = pubmed.search(doi=doi, delay=PAUSE)
        print(pmids)
        with open('pmids_lookup.csv', 'ab') as outfile:
            writer = csv.writer(outfile)
            writer.writerow([doi] + pmids)


if __name__ == '__main__':
    process_leiden_2018('publications-with JIFS-and-citations-2018-12-04-JR.csv')
