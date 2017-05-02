"Print the list of curators from the CSV file."

from __future__ import print_function

import csv

INFILENAME = 'Publikationer Faciliteten anv 2015 pmids.csv'
CURATOR_POS = 11

def get_curators():
    "Get the list of curators from the CSV file."
    curators = set()
    with open(INFILENAME, 'rb') as infile:
        reader = csv.reader(infile)
        reader.next()
        for record in reader:
            email = record[CURATOR_POS].strip()
            if email: curators.add(email.lower())
    return sorted(curators)

if __name__ == '__main__':
    curators = get_curators()
    print(len(curators))
    for email in curators:
        print(email)
