"Find non-imported publications in the CSV file."

from __future__ import print_function

import csv
import time

from publications import utils
from publications import pubmed
from publications.publication import PublicationSaver

INFILENAME = 'Facility publications 2016 pmids v3.csv'
OUTFILENAME = 'Facility publications 2016 nonimported.csv'
DOI_POS = 3
PMID_POS = 12
DELAY = 1.0

def get_args():
    parser = utils.get_command_line_parser(
        'Find non-imported publications in the CSV file.')
    return parser.parse_args()

def find_nonimported(db):
    with open(OUTFILENAME, 'wb') as outfile:
        writer = csv.writer(outfile)
        with open(INFILENAME, 'rb') as infile:
            reader = csv.reader(infile)
            writer.writerow(reader.next())
            for record in reader:
                pmid = record[PMID_POS].strip()
                if not pmid:
                    doi = record[DOI_POS].strip()
                    if doi:
                        print(doi)
                        time.sleep(DELAY)
                        pmids = pubmed.search(doi=doi)
                        if len(pmids) == 1:
                            record[PMID_POS] = pmids[0]
                            print(pmids[0])
                    writer.writerow(record)
                    outfile.flush()


if __name__ == '__main__':
    args = get_args()
    utils.load_settings(filepath=args.settings)
    db = utils.get_db()
    find_nonimported(db)
