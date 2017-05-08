Load data for publication year 2016
===================================

The database must have been initialized and the admin account created.


To do
-----

- Add labels for service, tech devel, collaboration.


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

### find_nonimported.py

Separate out the records from the CSV file that do not have a defined
PMID, and thus have not been imported so far.

### import_publications_doi.py

Using the DOI, try to find the PMID by search of PubMed. If found,
import using that data. Else import using the DOI.
