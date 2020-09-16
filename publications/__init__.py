"Publications: Simple publications reference database with web interface."

import os

__version__ = '3.3.5'

# Default settings, may be changed by a settings YAML file.
settings = dict(
    ROOT=os.path.dirname(__file__),
    BASE_URL='http://localhost:8885/',
    PORT=8885,
    TORNADO_DEBUG=False,
    LOGGING_DEBUG=False,
    LOGGING_FORMAT='%(levelname)s [%(asctime)s] %(message)s',
    DATABASE_SERVER='http://localhost:5984/',
    DATABASE_NAME='publications',
    COOKIE_SECRET=None,         # Must be set!
    PASSWORD_SALT=None,         # Must be set!
    EMAIL=dict(HOST=None,       # No emails can be sent unless this is set.
               PORT=None,
               TLS=False,
               USER=None,
               PASSWORD=None,
               SENDER=None),
    MIN_PASSWORD_LENGTH=6,
    LOGIN_MAX_AGE_DAYS=14,
    NCBI_DELAY = 0.5,             # Delay before PubMed fetch, to avoid block.
    NCBI_TIMEOUT = 5.0,           # Timeout limit for PubMed fetch.
    NCBI_API_KEY = None,          # NCBI account API key, if any.
    PUBLICATION_ACQUIRE_PERIOD=1,           # In days.
    PUBLICATIONS_FETCHED_LIMIT=10,
    PUBLICATION_QC_ASPECTS=['bibliography', 'xrefs'],
    SHORT_PUBLICATIONS_LIST_LIMIT=10,
    LONG_PUBLICATIONS_LIST_LIMIT=100,
    NUMBER_FIRST_AUTHORS=3,
    NUMBER_LAST_AUTHORS=2,
    DISPLAY_TRANSLATIONS={},
    SITE_NAME='Publications',
    SITE_TITLE='Publications',
    SITE_TEXT='A simple publications reference database system.',
    SITE_INSTRUCTIONS_URL='https://github.com/pekrau/Publications/wiki/Standard-operating-procedure',
    SITE_PARENT_URL=None,
    SITE_EMAIL=None,
    SITE_CONTACT='<p><i>No contact information available.</i></p>',
    SITE_DIR='static',
    SITE_LABEL_QUALIFIERS=[],
    SOURCE_URL='https://github.com/pekrau/Publications',
    SOURCE_VERSION=__version__,
    DOCS_URL='https://github.com/pekrau/Publications/wiki',
    XREF_TEMPLATE_URLS={
        'pmc': 'https://www.ncbi.nlm.nih.gov/pmc/articles/%s/',
        'bioproject': 'https://www.ncbi.nlm.nih.gov/bioproject/%s',
        'genbank': 'https://www.ncbi.nlm.nih.gov/nuccore/%s',
        'dryad': 'https://datadryad.org/resource/doi:%s'},
)
