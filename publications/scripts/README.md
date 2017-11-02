This directory contains some stand-alone scripts.

init_database.py
----------------

Initializes the database. The CouchDB instance must already exist, and
the account to connect with it must have been created and defined in
the settings file. **NOTE**: This will clobber any existing data!

load_designs.py
---------------

Loads the design view definitions, i.e. the JavaScript files defining
the indexes. This is a safe operation, no data will be changed.

create_admin.py
---------------

Create an account with the 'admin' role.

set_password.py
---------------

Set the password for an existing account.

dump.py
-------

Dumps the entires contents of the database in CouchDB, except for the
design documents.

search_pubmed.py
----------------

Search PubMed using specified criteria and fetch the references
setting them as unverified. Labels may be applied.

fetch_bulk.py
-------------
Fetch many publications given PMID/DOI, label and qualifier.
The publications are set as verified.

trawl_pubmed.py
---------------
Trawl PubMed for publications given a CSV file containing authors.
Produces a CSV file containing the aggregated publications references.
Does **not** fetch or otherwise import anything into the database.
