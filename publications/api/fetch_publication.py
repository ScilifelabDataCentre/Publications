"""Fetch a publication.
Given an identifier (PMID or DOI), ask the server to fetch the data 
for the publication and load it into the system.
If the publication already is in the system, add the given labels.
"""

from __future__ import print_function

# Third-party package
import requests


def fetch_publication(base_url, api_key, identifier,
                      verify=True, override=True, labels={}):
    """Fetch a publication. Return the IUID for the loaded publication.
    xid: the PubMed identifier (PMID) or Digital Object Identifier (DOI).
    verify: If true: sets the publication to be verified directly.
            If false: it is set as unverified.
    override: If true: fetch the publication even if it is blacklisted.
              If false: do not fetch if the publication is blacklisted.
    labels: A dictionary of labels to be assigned to the publication.
            For an entry in the dictionary, its key is the label, and its
            value is a string specifying the qualifier for that label.
    """
    url = "{base_url}/api/publication".format(base_url=base_url.rstrip('/'))
    headers = {'X-Publications-API-key': api_key}
    data = dict(identifier=identifier,
                verify=verify, override=override, labels=labels)
    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 200:
        raise ValueError("Error %s: %s" % (response.status_code,
                                           response.reason))
    else:
        return response.json()['href']


if __name__ == '__main__':
    import sys
    base_url = 'http://localhost:8885/'
    api_key = '81dfebb4caf54f6ab1eac63ff7c00382'
    labels = {'Bioinformatics Compute and Storage': 'Service',
              'My stuff': 'blah'}
    for identifier in sys.argv[1:]:
        print(fetch_publication(base_url, api_key, identifier, labels=labels))
