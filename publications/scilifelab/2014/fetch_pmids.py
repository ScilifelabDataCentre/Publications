"Fetch the XML files from PubMed."

from __future__ import print_function

import csv
import os

from publications import pubmed

INFILENAME = 'publikationer faciliteter 2010-2014 pmid v3.csv'
PMID_POS = 12
DIRNAME = 'entries'
DELAY = 1.0

with open(INFILENAME, 'rb') as infile:
    if not os.path.exists(DIRNAME):
        print('creating', DIRNAME)
        os.makedirs(DIRNAME)
    reader = csv.reader(infile)
    reader.next()
    count = 0
    count_none = 0
    pmids = set()
    for record in reader:
        pmid = record[PMID_POS]
        if pmid.startswith('['):
            pmid = ''
        if pmid and len(pmid) != 8:
            print('Incorrect length', pmid)
            pmid = ''
        if pmid:
            pmids.add(pmid)
            pubmed.fetch(pmid, dirname=DIRNAME, delay=DELAY)
            print('got', pmid)
            count += 1
        else:
            count_none += 1

print(len(pmids), 'unique PMIDs')
print(count, 'records with PMIDs')
print(count_none, 'records lacking PMIDs')
