This directory contains a number of stand-alone scripts for OrderPortal.

    init_database.py

Initializes the database. The CouchDB instance must already exist, and
the account to connect with it must have been created and defined in
the settings file. This will clobber any existing data!

    dump.py

Dumps the entires contents of the CouchDB instance, except for the
design documents.

    messenger.py

This is the script which sends out email messages according to recent
modifications of accounts and orders. It should be executed in a
regular fashion by cron.
