Publications
============

Simple web-based publications reference database system.

Features
--------

- Publications can be labeled to indicate e.g. research group, facility
  or some other classification.

- Direct import of publications from
  [PubMed](https://www.ncbi.nlm.nih.gov/pubmed) (with PMID) or
  [Crossref](https://www.crossref.org/) (with DOI).

- Script to search PubMed and fetch the publication references.
  Such publications are set as unverified.

- Curator accounts for editing the publication entries.

- Curators must verify publications that have been imported by scripts.

- Manual import, entry and/or edit of publication entries by curators.

- Curators can be assigned the privilege to apply a certain label to
  any publication.

- Trash registry to keep track of publications that have been deleted
  by curators as being irrelevant, and which should not be fetched again.

Installation
------------

- Install the required software.

- Edit your settings file.

- Create the database in the CouchDB system.

- Run the following scripts to initialize and to create the first account.

      $ python scripts/init_database.py
      $ python scripts/create_admin.py

- Set up the tornado web server to start on boot.

- Set a proxy from your outward-facing web server (Apache, nginx, etc)
  for the tornado server.

Implementation
--------------

Front-end: Bootstrap 3, jQuery, jQuery UI, DataTables

Back-end: Python 2.7, tornado, CouchDB, pyyaml, requests


Data for SciLifeLab
-------------------

Instructions for loading the data for SciLifeLab are given
in this [README](publications/scilifelab/README.md) and its
links.
