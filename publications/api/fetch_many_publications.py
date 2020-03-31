"""Fetch a publication.

Ask the server to fetch a publication into its database given a list
of PubMed identifiers (PMID) or DOI.

This code shows how a script can be used to interact with the API
fetch feature. The account needs to have an API key defined, which is
done in the web interface on the Edit account page.

The script can be used a standalone on the command line. This requires
changing the Publication server base URL and the API key.

The function defined in the script can be imported and used in your
own scripts.
"""

import time

# Third-party package
import requests


def fetch_publications(base_url, apikey, identifiers, labels={},
                       delay=3.0, debug=False):
    """Fetch a publication. Return the IUID for the loaded publication.

    identifiers: List of PubMed identifier (PMID) or 
                 Digital Object Identifier (DOI).

    labels: A dictionary of labels to be assigned to the publication.
            For an entry in the dictionary, its key is the label, and its
            value is a string specifying the qualifier for that label.
            Only valid labels (for the account) and qualifiers will be
            used, all others will be ignored.

    delay: The time to pause between calls to the API.

    debug: Print out success and failure after each fetch.

    Return a dict with an item 'success' containing the list of identifiers
    which were successfully fetched, and an item 'failure' containing the
    list of identifiers that were not fetched.
    """

    url = "{base_url}/api/publication".format(base_url=base_url.rstrip('/'))
    headers = {'X-Publications-API-key': apikey}

    success = []
    failure = []
    for identifier in identifiers:
        data = dict(identifier=identifier, labels=labels)
        time.sleep(delay)
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            if debug: print('failure:', identifier)
            failure.append(identifier)
        else:
            if debug: print('success:', identifier)
            success.append(identifier)
    return dict(success=success, failure=failure)


if __name__ == '__main__':
    import csv

    # Change to the Publications server
    base_url = 'https://publications-affiliated.scilifelab.se/'

    # API key is set for a specific account; see its web page.
    apikey = '1042c577166944dfa59b977ec31230e7'

    # Labels to use for the publication.
    # Labels not allowed for the account will be ignored.
    # Invalid qualifier values will be changed to None.
    labels = {'Affiliated researcher': None}

    # PMIDs from CSV file.
    # with open('pmids_one.csv', 'rb') as infile:
    #     reader = csv.reader(infile)
    #     pmids = [r[1] for r in reader]
    # print(len(pmids))

    # DOIs from CSV file.
    with open('pmids_zero.csv', 'rb') as infile:
        reader = csv.reader(infile)
        pmids = [r[0] for r in reader]
    print(len(pmids))

    # Skip to after last loaded before break (ConnectionError)
    # for pos, pmid in enumerate(pmids):
    #     if pmid == '26071243':
    #         pmids = pmids[pos+1:]

    print(len(pmids))
    fetch_publications(base_url, apikey, identifiers=pmids, 
                       labels=labels, debug=True)
