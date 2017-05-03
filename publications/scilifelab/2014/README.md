Load data for publication year 2017
===================================

The database must have been initialized and the admin account created.


To do
-----

- NOTHING DONE YET.
- Add labels for service, tech devel, collaboration.
- Add those with DOI but not PMID.
- Resolve the rest.


Main loading scripts
--------------------

### add_pmid.py

Add PMID to each row of the CSV file using the given DOI and CrossRef.


### fetch_pmids.py

Fetch the XML files from PubMed using the PMIDs in the CSV file.


### create_curators_labels.py

Create the curators in the database and their labels from the CSV file.


### import_publications.py

Import publications having PMIDs in the CSV file. Use the files downloaded
by the fetch_pmids.py script, if done.
