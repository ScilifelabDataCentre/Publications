Publications
============

Simple web-based publications reference database system.

Features
--------

- Publication references can be added by fetching data from:

  - [PubMed](https://www.ncbi.nlm.nih.gov/pubmed)
    using the PubMed identifier (PMID).
  - [Crossref](https://www.crossref.org/)
     using the Digital Object Identifier (DOI).

- Publication references can be added manually.

- Publication references can be labeled. The labels can be used to indicate
  e.g. research group, facility or some other classification.

- There are curator accounts for editing the publication entries.
  Currently, only the admins can create curator accounts;
   it is not possible to register for one.

- Curators can fetch publications or add manually.

- All curators can change every publication reference.

- A curator can assign only the labels that she has been assigned by the
  admin.

- Publication references can be set as unverified when loading them
  by automated scripts. A curator must then verify each such publication.

- There is a blacklist registry based on the PMID and/or DOI of publications.
  This is used to avoid re-importing publications that have already been
  determined to be irrelevant for the database.

- The data can be extracted in JSON and CSV formats. The CSV format allows
  some basic filtering options.

Installation
------------

- Install the required software:
  - Python 2.7
  - tornado
  - CouchDB
  - pyyaml
  - requests

- Create the database in the CouchDB system.

- Edit your settings file, specifying the CouchDB connection, site name, etc.

- Run the following scripts to initialize and to create the first account.

      $ python scripts/init_database.py
      $ python scripts/create_admin.py

- Set up the tornado web server to start on boot.

- Set a proxy from your outward-facing web server (Apache, nginx, or whatever
  your site supports) for the tornado server.

Implementation
--------------

Front-end: Bootstrap 3, jQuery, jQuery UI, DataTables

Back-end: Python 2.7, tornado, CouchDB, pyyaml, requests


SciLifeLab
----------

The system was designed for keeping track of the publications
to which the facilities of SciLifeLab contributed.
See [SciLifeLab Publications](https://publications.scilifelab.se/).

The data is available at [README](publications/scilifelab/README.md).
