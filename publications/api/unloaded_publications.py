"""Go through publications in CSV file, identify those that do not seem to have
been imported into the database.
"""

import csv
from collections import OrderedDict

# Third-party package
import requests


def loaded(base_url, identifier):
    url = "%s/search.json" % base_url.rstrip('/')
    response = requests.get(url, params=dict(terms=identifier))
    if response.status_code != 200:
        raise ValueError("Error %s: %s" % (response.status_code,
                                           response.reason))
    else:
        try:
            return response.json()['publications_count']
        except KeyError:
            return 0


if __name__ == '__main__':
    # Change to the Publications server
    base_url = 'https://publications-affiliated.scilifelab.se/'

    unloaded = OrderedDict()

    for csvfilename in ['publications_affiliated.csv',
                        'publications_fellows.csv']:
        with open(csvfilename, 'rb') as infile:
            reader = csv.reader(infile)
            header = next(reader)
            for row in reader:
                identifier = row[9].strip()
                if identifier == 'NULL':
                    unloaded["NULL %i" % len(unloaded)] = row
                elif not loaded(base_url, identifier):
                    unloaded[identifier] = row
                    print('>>>', identifier)
                else:
                    print('loaded', identifier)

    with open('unloaded.csv', 'wb') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(header)
        for row in list(unloaded.values()):
            writer.writerow(row)
