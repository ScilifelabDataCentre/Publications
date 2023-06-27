# Overview

The Publications system stores references to publications and allows
labelling them. It does **not** store PDFs of publications.

The Publications system is appropriate for keeping track of the
publications for a group, a project, an institute, a department, or
similar.

A publication reference ('publication' in short) may contain:
- Title.
- Author by name and with ORCID reference, if available.
- Abstract.
- Bibliographic data; publication date, volume, pages, etc.
- References to external database entries (xrefs).
- Labels; annotation added by the curators.

Publications are added by providing DOI (Digital Object Identifier) or
PMID (PubMed identifier) which the Publications system then fetches
the data for from the Crossref and/or PubMed web services.

# User account

Only a user with a valid account may add and edit publications.

It is not possible to register an account by oneself in the system.To
get an account one must contact the site admin; see the [Contact page](/contact).

There are two user account roles in the Publications system: **admin** and **curator**.

## Admin

An admin (also called site administrator) is an account in the system
with all available privileges, including creating, enabling and
disabling curator accounts.

Only the admin can edit labels and assign them to curators. The admin
can add, edit, delete and blacklist publication references.

Contact information for you admin is available in the [Contact page](/contact).

## Curator

A curator is an account in the system with the privileges to add,
edit, delete and blacklist publication references, and to add the
labels which it has been assigned by the admin.

A curator account requires login. It is created by the admin. It is
not possible to register one's own account.

# Add publication

## Log in to your account

In order to add publications to this system, you have to be logged
in to your account in the system. If you do not have one, request
it by contacting the system administrator given in
the [Contact page](/contact).

## Add publication by fetching data

**This is the recommended procedure for adding a publication.**

Publication references should be added using the
[Fetch data for publication page](/fetch). In that page, do the following:

- Enter the Digital Object Identifiers (DOI) and/or PubMed
  identifiers (PMID) of the publications to be added.
- Use the checkboxes to denote which labels should be applied to the publications.
  Also select the applicable qualifier (if enabled in your site).
- When clicking "Fetch", the system goes to the web services at
  [Crossref](https://www.crossref.org/) and/or
  [PubMed](https://pubmed.ncbi.nlm.nih.gov/), respectively,
  to fetch the publication reference data.
- This procedure checks whether the DOI or PMID already exists in the
  database, in order to avoid multiple copies. The labels and qualifiers
  will be applied to entries that already exist in the database, as if they had
  been added by the operation.

## Add publication manually

Publication references can be added manually by filling in a form on
the [Add publication manually page](/add).  This is for publication
that has neither a DOI nor a PMID, often preprints.

# Edit publication

It is possible to edit the details of a publication. However, this is
**strongly discouraged**. It is much more preferable to update
contents from PubMed or Crossref.

If a publication as been wrongly marked using a label that you
control, then **do not delete the publication**. Instead, edit the
publication to remove the offending label.

# Delete publication

A curator may delete any publication. Please note that this is a
**global** operation, affecting the entire database.

This should therefore be done **only** if the publication is clearly
irrelevant for the site as a whole, or if it is a duplicate.

# Multiple copies

Multiple copies of a publication reference are, of course, bad news.
The Publications system tries to avoid creating duplicates when
performing fetch by checking for already loaded DOIs and PMIDs.

However, duplicates may nevertheless be created by mistake, for
example when adding a reference manually that in fact has already been
added.

A curator may view the [Duplicates page](/publications/duplicates),
which uses a heuristic algorithm to identify possible duplicates.

A curator has to edit and/or delete the duplicated entries by hand to
remove the offending entry. Note that labels may have to be
transferred from the publication that is to be deleted to the one that
is to be kept. This may require site administrator privileges.

# Label

Labels are annotation tagged on to the publication references. They
can be used to denote *e.g.* which facility unit or research
group was involved in a publication, or what area the publication is
in. The set of labels are controlled by the site administrator.

Note that the term "label" may be configured by the site administrator
to be translated into some other term in your site. For example,
the [SciLifeLab Infrastructure Units Publications instance](https://publications.scilifelab.se/)
uses the term "Infrastructure Unit" instead of "label".

A curator account can have privileges for a set of labels. This
means that she can add or remove those labels to a publication. She
cannot change the labels for which she does not have privileges.

## Qualifier

Labels may have qualifiers, which can be used to denote *e.g.*
what type of involvement a facility unit had with the publication.

The available qualifiers are part of the configuration of a site
and are set by the site administrator, who may also disable the use
if qualifiers entirely.


# Xref

An xref is a reference to an external resource, most often a database
entry. Ideally, the external reosuce should be accessible on the
web. The reference consists of two parts: The external database and
the accession code for the entry in it.

In those cases where the external database provides a URL template,
the Publications system can be configured to allow the button in the
interface to open a new browser tab for the database entry.

There is currently also an optional free-text description field
associated with an xref. This may be used for a brief characterization
of the data available in the database entry.

# Subset

A subset of publications may be obtained by executing a selection
expression in the [Subset page](/subset).

The selection expression works by using functions which select a subset of all
publications currently in the system. Operators can be used to combine
these subsets. Paranthesis are used to determine the order of evaluation
if the operators. A selection expression may be arbitrarily complex.

The list of selected publications can be viewed or downloaded in different
file formats.

The details of the subset feature are documented in the [Subset page](/subset).

# Blacklist

The blacklist is a list of PubMed identifiers and DOI's of publication
references that should not be fetched into the database.

The idea is that a curator should be able to decide that a specific
publication reference is clearly irrelevant for the database, delete
the entry from the database, and simultaneously ensure that it does
not get added at a later stage.

A curator may override a blacklist entry by explicitly checking an
input box in the fetch page. This is to allow rescinding a previous
decision, and should be used with care.

The list of current entries in the blacklist can be viewed in the
[Blacklisted page](/blacklisted). A curator may delete entries from
the blacklist.

# API

The Python code examples below use the third-party package
[requests](https://docs.python-requests.org/en/latest/).

## Fetch publication

- **URL**: `/publication`
- **Method**: `POST`
- **Payload**: JSON
  ```
  {
     "identifier": "<PMID or DOI>",
     "labels": {"<labelname>": "<optional qualifier>"}
  }
  ```
- **Description**: The server is instructed to to fetch publication data
  from PubMed or Crossref given a PubMed identifier (PMID) or Digital
  Object Identifier (DOI). This API call fetches only one publication
  at a time. The `labels` item in the payload is optional.
- **Example code**:
  ```
  import json
  import requests

  url = "http://your-server/api/publication"
  headers = {'X-API-key': "my-API-key"}

  data = dict(identifier="1557129",  # PMID identifier in this example.
              labels={"MyLab": "Collaboration"})

  response = requests.post(url, headers=headers, json=data)

  if response.status_code != 200:
      raise ValueError(f"Error {response.status_code}: {response.reason}")
  else:
      print(json.dumps(response.json(), indent=2))
  ```

## Change labels

- **URL**: `/publication/{iuid}/labels`
- **Method**: `POST`
- **Payload**: JSON body
  ```
  {
     "labels": {"<labelname>": "<optional qualifier>"}
  }
  ```
- **Description**: Change the labels of the given publication. The labels provided
   must contain all labels to be set for the publication among
   those that the account specified by the API key can edit. That
   is, if the user account has three labels associated with it, and only
   two of those are specified, then the third will be removed if it
   was already present for the publication.
- **Example code**:
  ```
  import json
  import requests

  url = "http://your-server/api/publication/{publication-iuid}/labels"
  headers = {'X-API-key': "my-API-key"}

  data = dict(labels={"MyLab": "Service"})

  response = requests.post(url, headers=headers, json=data)

  if response.status_code != 200:
      raise ValueError(f"Error {response.status_code}: {response.reason}")
  else:
      print(json.dumps(response.json(), indent=2))
  ```
