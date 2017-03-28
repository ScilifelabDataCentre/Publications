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

dump.py
-------

Dumps the entires contents of the database in CouchDB, except for the
design documents.

search_pubmed.py
----------------

Search PubMed using specified criteria and fetch the references
setting them as unverified. Labels may be applied.
