"Fetch the XML files from PubMed."

from __future__ import print_function

import csv

from publications import pubmed

INFILENAME = 'Publikationer Faciliteten anv 2015 pmids.csv'
PMID_POS = 14
DIRNAME = 'entries'
DELAY = 1.0

with open(INFILENAME, 'rb') as infile:
    reader = csv.reader(infile)
    reader.next()
    count = 0
    count_none = 0
    for record in reader:
        pmid = record[PMID_POS]
        if pmid.startswith('['):
            pmid = None
        if pmid:
            pubmed.fetch(pmid, dirname=DIRNAME, delay=DELAY)
            print('got', pmid)
            count += 1
        else:
            count_none += 1

print(count, 'PMIDs')
print(count_none, 'lacking PMIDs')
