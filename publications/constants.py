"Various constants."

from __future__ import print_function

import re

# Patterns
ID_RX    = re.compile(r'^[a-z][_a-z0-9]*$', re.IGNORECASE)
NAME_RX  = re.compile(r'^[^/]+$')
IUID_RX  = re.compile(r'^[0-9a-f]{32}$')
DATE_RX  = re.compile(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}$') # Safe until 9999 CE...
EMAIL_RX = re.compile(r'^[^@]+@[^@]+\.[^@]+$')
PMID_RX  = re.compile(r'^[1-9]\d*$')

# CouchDB
# For view ranges: CouchDB uses the Unicode Collation Algorithm,
# which is not the same as the ASCII collation sequence.
# The endkey is inclusive, by default.
CEILING = 'ZZZZZZZZ'

# Entity documents
DOCTYPE     = 'publications_doctype'
PUBLICATION = 'publication'
JOURNAL     = 'journal'
ACCOUNT     = 'account'
LABEL       = 'label'
BLACKLIST   = 'blacklist'
LOG         = 'log'
ENTITIES    = (PUBLICATION, JOURNAL, ACCOUNT, LABEL)

# Account roles
ADMIN    = 'admin'
CURATOR  = 'curator'
ROLES    = (ADMIN, CURATOR)

# Boolean string values
TRUE  = frozenset(['true', 'yes', 't', 'y', '1'])
FALSE = frozenset(['false', 'no', 'f', 'n', '0'])

# User login account
USER_COOKIE    = 'publications_user'
API_KEY_HEADER = 'X-Publications-API-key'

# Content types (MIME types)
HTML_MIME = 'text/html'
JSON_MIME = 'application/json'
CSV_MIME  = 'text/csv'

# Various texts.
FETCH_ERROR = 'Could not fetch data. '
BLACKLISTED_MESSAGE = "Publication(s) not fetched since in the blacklist." \
                      " Check 'override' and try again, if needed: "

# External URL templates.
PUBMED_URL = 'https://www.ncbi.nlm.nih.gov/pubmed/%s'
DOI_URL    = 'https://doi.org/%s'

# Search setup; characters to remove and words to ignore.
SEARCH_REMOVE = "-_\.:,?()'$"
SEARCH_IGNORE = [
    'a',
    'an',
    'and',
    'are',
    'as',
    'at',
    'but',
    'by',
    'can',
    'for',
    'from',
    'into',
    'in',
    'is',
    'it',
    'of',
    'on',
    'or',
    'that',
    'the',
    'to',
    'using',
    'with',
    ]
