"Various constants."

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
ACCOUNT     = 'account'
TRASH       = 'trash'
LOG         = 'log'
ENTITIES    = (PUBLICATION, ACCOUNT)

# Account roles
ADMIN = 'admin'
CURATOR  = 'curator'
ROLES = (ADMIN, CURATOR)

# Boolean string values
TRUE  = frozenset(['true', 'yes', 't', 'y', '1'])
FALSE = frozenset(['false', 'no', 'f', 'n', '0'])

# User login account
USER_COOKIE    = 'publications_user'
API_KEY_HEADER = 'X-Publications-API-key'
