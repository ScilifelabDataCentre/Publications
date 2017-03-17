This directory contains stand-alone scripts for Publications.

    init_database.py

Initializes the database. The CouchDB instance must already exist, and
the account to connect with it must have been created and defined in
the settings file. This will clobber any existing data!

    dump.py

Dumps the entires contents of the CouchDB instance, except for the
design documents.
