Load data for publication year 2017
===================================

The database must have been initialized and the admin account created.

The v3 file was copied from v2 and edited manually to include more PMIDs
found by manual searches.

The DOIs in the v3 file were imported manually.


To do
-----

- Input the few remaining by hand. A few patents.


Main loading scripts
--------------------

### add_pmid.py

Add PMID to each row of the CSV file using the given DOI and CrossRef.

Copied result to 'publikationer faciliteter 2010-2014 pmid v2.csv'
and edited away some garbage, such as empty lines and title 'N/A'.

### fetch_pmids.py

Fetch the XML files from PubMed using the PMIDs in the CSV file.


### create_labels.py

Create the labels in the database from the CSV file.


### import_publications.py

Import publications having PMIDs in the CSV file. Use the files downloaded
by the fetch_pmids.py script, if done. This script also handles the few
DOI-only publications in the input CSV file.

