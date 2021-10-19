"Publications: A publications reference database with web interface."

import os

__version__ = "6.5.4"

ROOT = os.path.dirname(os.path.abspath(__file__))

# Default settings, may be changed by a settings YAML file.
settings = dict(
    ROOT=ROOT,
    BASE_URL="http://localhost:8885/",
    PORT=8885,                  # The port used by tornado
    TORNADO_DEBUG=False,
    LOGGING_DEBUG=False,
    LOGGING_FORMAT="%(levelname)s [%(asctime)s] %(message)s",
    PIDFILE=None,
    DATABASE_SERVER="http://localhost:5984/",
    DATABASE_NAME="publications",
    DATABASE_ACCOUNT=None,      # Should probably be set to connect to CouchDB.
    DATABASE_PASSWORD=None,     # Should probably be set to connect to CouchDB.
    COOKIE_SECRET=None,         # Must be set!
    PASSWORD_SALT=None,         # Must be set!
    EMAIL=None,                 # No emails can be sent unless this is set.
    MIN_PASSWORD_LENGTH=6,
    LOGIN_MAX_AGE_DAYS=14,
    PUBMED_DELAY=0.5,           # Delay before PubMed fetch, to avoid block.
    PUBMED_TIMEOUT=5.0,         # Timeout limit for PubMed fetch.
    NCBI_API_KEY=None,          # NCBI account API key, if any.
    CROSSREF_DELAY=0.5,         # Delay before Crossref fetch, to avoid block.
    CROSSREF_TIMEOUT=10.0,      # Timeout limit for Crossref fetch.
    PUBLICATIONS_FETCHED_LIMIT=10,
    SHORT_PUBLICATIONS_LIST_LIMIT=10,
    LONG_PUBLICATIONS_LIST_LIMIT=200,
    TEMPORAL_LABELS=False,
    FIRST_YEAR=2010,
    MAX_NUMBER_LABELS_PRECHECKED=2,
    NUMBER_FIRST_AUTHORS=3,
    NUMBER_LAST_AUTHORS=2,
    DISPLAY_TRANSLATIONS={},
    SITE_NAME="Publications",
    SITE_TITLE="Publications",
    SITE_TEXT="A publications reference database system.",
    SITE_PARENT_NAME="Site host",
    SITE_PARENT_URL=None,
    SITE_EMAIL=None,
    SITE_CONTACT="<p><i>No contact information available.</i></p>",
    SITE_STATIC_DIR=os.path.normpath(os.path.join(ROOT, "../site/static")),
    SITE_LABEL_QUALIFIERS=[],
    SOURCE_URL="https://github.com/pekrau/Publications",
    SOURCE_VERSION=__version__,
    IDENTIFIER_PREFIXES=["doi:", 
                         "pmid:",
                         "pubmed:", 
                         "http://doi.org/",
                         "https://doi.org/",
                         "http://dx.doi.org/"],
    XREF_TEMPLATE_URLS={
        "PMC": "https://www.ncbi.nlm.nih.gov/pmc/articles/%s/",
        "BioProject": "https://www.ncbi.nlm.nih.gov/bioproject/%s",
        "Genbank": "https://www.ncbi.nlm.nih.gov/nuccore/%s",
        "GEO": "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=%s",
        "pmc": "https://www.ncbi.nlm.nih.gov/pmc/articles/%s",
        "PDB": "https://www.rcsb.org/structure/%s/",
        "PubChem-Substance": "https://pubchem.ncbi.nlm.nih.gov/substance/%s",
        "ArrayExpress": "https://www.ebi.ac.uk/arrayexpress/experiments/%s/",
        "EBI": "https://www.ebi.ac.uk/ebisearch/search.ebi?db=allebi&query=%s",
        "Dryad": "https://datadryad.org/search?q=%s",
        "Mendeley": "https://doi.org/%s",
        "figshare": "https://doi.org/%s",
        "Zenodo": "https://doi.org/%s",
    },
)
