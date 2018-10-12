This directory contains example scripts for interacting with the
system via the web API. The third-party package `requests` is used.

fetch_publication.py
------------------

Ask the server to fetch a publication into its database given the
PubMed identifier (PMID) or DOI.

This code shows how a script can be used to interact with the API
fetch feature. The account needs to have an API key defined, which is
done in the web interface on the Edit account page.

The script can be used a standalone on the command line. This requires
changing the Publication server base URL and the API key.

The function defined in the script can be imported and used in your
own scripts.
