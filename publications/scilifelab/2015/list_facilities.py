"Compile the list of facilities from the CSV file."

from __future__ import print_function

import csv

INFILENAME = 'Publikationer Faciliteten anv 2015 pmids.csv'
FACILITY_POS = 2

def get_facilities():
    "Get the list of facilities from the CSV file."
    facilities = set()
    with open(INFILENAME, 'rb') as infile:
        reader = csv.reader(infile)
        reader.next()
        for record in reader:
            name = record[FACILITY_POS].strip()
            if name: facilities.add(name)
    return sorted(facilities)

if __name__ == '__main__':
    facilities = get_facilities()
    print(len(facilities))
    for name in facilities:
        print(name)
