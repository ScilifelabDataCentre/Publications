This directory contains some stand-alone scripts that interact
directly with the database. These do *NOT* use the web API.

init_database.py
----------------

Initializes the database. The CouchDB instance must already exist, and
the CouchDB account to connect with it must have been created and
defined in the settings file. **NOTE**: This will clobber any existing
data!

load_designs.py
---------------

Loads the design view definitions, i.e. the JavaScript files defining
the indexes. This is a safe operation, no data will be changed.

create_admin.py
---------------

Create an account with the 'admin' role.

create_curator.py
---------------

Create an account with the 'curator' role.

set_password.py
---------------

Set the password for an existing account.

dump.py
-------

Dumps the entires contents of the database in CouchDB, except for the
design documents.

fetch_bulk.py
-------------
Fetch publications in bulk from CSV file containing PMID/DOI, label 
and qualifier. The publications are set as verified.

trawl_pubmed.py
---------------
Trawl PubMed for publications given a CSV file containing authors.
Produces a CSV file containing the aggregated publications references.
Does **not** fetch or otherwise import anything into the database.

check_duplicates.py
-------------------
Check for duplicates based on comparing 4 longest words in the title.
A fast and dirty comparison algorithm.

fix_missing_pmids.py
--------------------
Fix missing PMID in all publications by searching for title.
