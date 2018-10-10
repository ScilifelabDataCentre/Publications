"""Fetch a publication.

Script to fetch a publication given by PMID or DOI on the command line.
The server is requested to fetch the data for the publication and load it.
If the publication already is in the system, the given labels are added.

NOTE: The function 'fetch_publication' can be imported and used in scripts.
"""

from __future__ import print_function

# Third-party package
import requests


def fetch_publication(base_url, apikey, identifier, override=False, labels={}):
    """Fetch a publication. Return the IUID for the loaded publication.

    identifier: PubMed identifier (PMID) or Digital Object Identifier (DOI).

    override: If true: fetch the publication even if it is blacklisted.
              If false: do not fetch if the publication is blacklisted.

    labels: A dictionary of labels to be assigned to the publication.
            For an entry in the dictionary, its key is the label, and its
            value is a string specifying the qualifier for that label.
            Only valid labels (for the account) and qualifiers will be
            used, all others will be ignored.
    Response HTTP status 200 when successful, and the response body
    contains the JSON representation of the publication.
    Response HTTP status 400 is returned when the PMID or DOI was bad
    or the external server (PubMed, Crossref) could not be reached.
    Response HTTP status 409 is returned when the publication is blacklisted
    (and override was False), 
    """

    url = "{base_url}/api/publication".format(base_url=base_url.rstrip('/'))
    headers = {'X-Publications-API-key': apikey}
    data = dict(identifier=identifier, override=override, labels=labels)

    response = requests.post(url, headers=headers, json=data)

    if response.status_code != 200:
        raise ValueError("Error %s: %s" % (response.status_code,
                                           response.reason))
    else:
        return response.json()['href']


if __name__ == '__main__':
    import sys

    # Change to the Publications server
    base_url = 'http://localhost:8885/'

    # API key is set for a specific account; see its web page.
    apikey = '81dfebb4caf54f6ab1eac63ff7c00382'

    # Labels to use for the publication.
    # Labels not allowed for the account will be ignored.
    # Invalid qualifier values will be changed to None.
    labels = {'Bioinformatics Compute and Storage': 'Service',
              'My stuff': 'Service'}

    # Command line arguments are PMIDs or DOIs.
    for identifier in sys.argv[1:]:
        print(fetch_publication(base_url, apikey, identifier, labels=labels))
