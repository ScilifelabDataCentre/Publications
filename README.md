Publications
============

A web-based publications reference database system.

Requires Python 3.6 or higher.

See **[Important changes](#important-changes)**

Features
--------

- All publication reference data is visible to all. No login is
  required for viewing.

- Publication references can be added by fetching data from:

  - [PubMed](https://www.ncbi.nlm.nih.gov/pubmed)
    using the PubMed identifier (PMID).
  - [Crossref](https://www.crossref.org/)
     using the Digital Object Identifier (DOI).

- Publication references can be added manually.

- A powerful subset selection expression evaluator, to produce a wide
  range of publication subsets from the data. New in version 6.0.

- Curator accounts for adding and editing the publication entries can
  be created by the admin of the instance.

- All curators can edit every publication reference. There is a log
  for each publication, so it is possible to see who did what when.

- Publication references can be labeled. The labels can be used to
  indicate e.g. research group, facility or some other classification.
  A label can have a qualifier, e.g. to denote if the publication was
  due to facility service or to a collaboration.

- A curator can use only the labels that she has been assigned by the
  admin.

- There is a blacklist registry based on the PMID and/or DOI of
  publications.  When a publication is blacklisted, it will not be
  fetched when using PMID, DOI or automatic scripts. This is to avoid
  adding publications that have already been determined to be
  irrelevant.

- Researcher entity, which can be associated with a publication.
  This is done automatically if the PubMed or Crossref data specifies
  ORCID for a publication author. New in version 4.0.

- Allow setting a flag 'Open Access' for a publication. New in version 4.0.

- The publications data can be extracted in JSON, CSV, XLSX and TXT formats.

- API to ask the server to fetch publications from PubMed or Crossref.
  See [its README](https://github.com/pekrau/Publications/tree/master/publications/api).

Important changes
-----------------

- Since version 6.4, the GitHub wiki has been discontinued. Installation
  information is available below, and other information is available
  in the web app interface.

- Since version 6.3, the directory containing site-specific data
  (e.g. `settings.yaml`, `static` directory for favicon and logo image files)
  has been moved from `Publications/publications/site` to `Publications/site`.
  The installation procedure has changed accordingly.

- Since version 6.0, the Python module
  [CouchDB2](https://pypi.org/project/CouchDB2/) is used instead of
  [CouchDB](https://pypi.org/project/CouchDB/). Upgrade your packages
  according to the `requirements.txt`.

Implementation
--------------

### Front-end (via CDN's)

- [Bootstrap 3](https://getbootstrap.com/docs/3.4/)
- [jQuery](https://jquery.com/)
- [jQuery UI](https://jqueryui.com/)
- [DataTables](https://datatables.net/)

### Back-end (installed on server)

- [Python 3.6](https://www.python.org/)
- [tornado](http://www.tornadoweb.org/en/stable/)
- [CouchDB server](http://couchdb.apache.org/)
- [CouchDB2](https://pypi.python.org/pypi/CouchDB2/)
  (changed from [CouchDB 1.2](https://pypi.org/project/CouchDB/)
   in version 6.0)
- [pyyaml](https://pypi.python.org/pypi/PyYAML)
- [requests](http://docs.python-requests.org/en/master/)

Installation
------------

0. NOTE: tornado is difficult (even impossible?) to set up on Windows
   systems, so Linux is strongly recommended.

1. Ensure that you have Python 3.6 or higher.

2. Your Python environment must include the Publications directory in
   its path, e.g.:
   ```
   $ cd wherever/Publications
   $ export PYTHONPATH=$PWd
   ```

3. Install the required Python modules (see `Publications/requirements.txt`)

4. Ensure that you have the CouchDB server installed and running.

5. Create the database publications in the CouchDB server using its
   own interface. Ensure that the database allows read/write access
   for the CouchDB server account of your choice.  Record the CouchDB
   server account name and password for the `settings.yaml` file (see below).

6. Copy the directory `Publications/site_template` and all its contents to
   `Publications/site`. The latter directory contains files that can or
   should be modified for your site.

7. Edit your settings file `Publications/site/settings.yaml`.
   In particular, set the CouchDB connection, site name, etc.

8. The Publications CouchDB database must be initialized using the CLI.
   This also tests that the CouchDB variables in the `settings.yaml`
   file are correct.

   `$ python cli.py initialize `
   
9. Create an admin account using the CLI. This admin account is needed to
   create other accounts (admin or curator) in the web interface.

   `$ python cli.py admin`

10. Set up the tornado web server to start on boot, using the port
    number you have defined in the `settings.yaml` file. You need to figure
    this out yourself.

11. Set a proxy from your outward-facing web server (Apache, nginx, or
    whatever your site supports) for the tornado server. You need to figure
    this out yourself.

SciLifeLab
----------

The system was designed for keeping track of
[publications to which the infrastructure units of SciLifeLab](https://publications.scilifelab.se/)
contributed.

Another instance is used to keep track of
[Covid-19-related research papers](https://publications-covid19.scilifelab.se/)
from Sweden.
