This directory contains stand-alone scripts to be executed from
the command line. They interact directly with the database.

init_database.py
----------------

Initialize the CouchDB database instance.

**Note**: The CouchDB database must exist.

1) Wipes out the old database, using the slow method of deleting
   each document in turn. Consider instead doing database delete
   from the CouchDB interface.
2) Loads the design documents (view index definitions).

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

Dump the database into a tar.gz file.

The settings file may be given as a command line option, otherwise it
is obtained as usual.

By default, the dump file will be called `dump_{ISO date}.tar.gz`
using today's date. It will be written to the current directory
unless the `--dumpdir` is used.

Alternatively, the `--dumpfile` argument defines the full file path.

undump.py
---------

Load a dump tar file into the CouchDB database.

The settings file may be given as a command line option,
otherwise it is obtained as usual.

The file to load must be given as a command line argument.

**Note**: The dabase instance must exist, and should be empty. If it
is not empty, this script may overwrite existing documents.

fetch_bulk.py
-------------

Fetch publications in bulk given a CSV file with PMID/DOI,
label and qualifier.

trawl_pubmed.py
---------------

Trawl PubMed for publications given a CSV file containing authors.
Produces a CSV file containing the aggregated publications references.
There is no interaction with the database; nothing is loaded into it.

**Note**: This is a stand-alone script without any external dependencies,
except for the third-party Python package 'requests'. In particular,
the pubmed module has been inlined here. This makes it easy to just
use this script without having to download the entire package.

check_duplicates.py
-------------------

Check for duplicates based on comparing 4 longest words in the title.
A fast and dirty comparison algorithm. Will produce som false positives.

fix_missing_pmids.py
--------------------

Try to fix missing PMID in all publications by searching for title.
