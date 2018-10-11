This directory contains some stand-alone scripts that interact
directly with the database. These do *NOT* use the web API.

init_database.py
----------------

Initializes the database, and loads the design documents (view index
definitions). The CouchDB instance must already exist, and the CouchDB
account to connect to it must have been created and defined in the
settings file. **NOTE**: This will clobber any existing data!

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

undump.py
---------

Reads a dump file into the CouchDB database. It assumes that the database
is empty. If it is not, it may overwrite existing data, which is a bad idea.

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
