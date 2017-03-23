Publications
============

Simple web-based publications reference database system.
Curators may add or fetch publications.
Publications can be labeled to indicate e.g. research group, facility,
or some other classification.

Features
--------

- Direct fetch of publications by PMID or DOI from
  [PubMed](https://www.ncbi.nlm.nih.gov/pubmed) or
  [Crossref](https://www.crossref.org/).

- Manual edit of publication entry.

- Trash registry to keep track of publications that have been deleted.

- Ability to override trash registry manually.

Implementation
--------------

Front-end: Bootstrap 3, jQuery, jQuery UI, DataTables

Back-end: Python 2.6 or 2.7, tornado, CouchDB, pyyaml, requests
