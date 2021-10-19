Publications
============

A web-based publications reference database system.

- **[Features](#features)**
- **[Important changes](#important-changes)**
- **[Implementation](#implementation)**
- **[Installation](#installation)**
- **[Command-line interface](#command-line-interface)**
- **[Example instances](#example-instances)**


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

This system requires Python 3.6 or higher.

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
   ```
   $ python cli.py initialize
   ```
   
9. Create an admin account using the CLI. This admin account is needed to
   create other accounts (admin or curator) in the web interface.
   ```
   $ python cli.py admin
   ```

10. Set up the tornado web server to start on boot, using the port
    number you have defined in the `settings.yaml` file. You need to figure
    this out yourself.

11. Set a proxy from your outward-facing web server (Apache, nginx, or
    whatever your site supports) for the tornado server. You need to figure
    this out yourself.

Command-line interface
----------------------

There is a command-line interface (CLI) for admin work on the machine
the system is running on. See its help texts. The top-level help text is:

```
$ python cli.py --help
Usage: cli.py [OPTIONS] COMMAND [ARGS]...

Options:
  -s, --settings TEXT  Name of settings YAML file.
  --log                Enable logging output.
  --help               Show this message and exit.

Commands:
  add-label        Add a label to a set of publications.
  admin            Create a user account having the admin role.
  counts           Output counts of database entities.
  curator          Create a user account having the curator role.
  dump             Dump all data in the database to a .tar.gz dump file.
  fetch            Fetch publications given a file containing PMIDs...
  find-pmid        Find the PMID for the publications in the CSV file.
  initialize       Initialize the database, which must exist; load all...
  password         Set the password for the given account.
  remove-label     Remove a label from a set of publications.
  select           Select a subset of publications and output to a file.
  show             Display the JSON for the single item in the database.
  undump           Load a Publications database .tar.gz dump file.
  update-crossref  Use Crossref to update the publications in the CSV file.
  update-pubmed    Use PubMed to update the publications in the CSV file.
  xrefs            Output all xrefs as CSV data to the given file.
```

Example instances
-----------------

- [SciLifeLab Infrastructure Units Publications](https://publications.scilifelab.se/)
  which keeps track of the publications to which the infrastructure
  units of SciLifeLab have contributed. This was the need that the
  system was designed for.

- [Covid-19 Publications](https://publications-covid19.scilifelab.se/)
  for publications with contributions from Swedish research.
