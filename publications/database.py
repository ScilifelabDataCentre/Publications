"CouchDB operations."

import logging

import couchdb2

from publications import constants
from publications import settings
from publications import utils


def get_dbserver():
    "Return the CouchDB2 handle for the CouchDB server."
    kwargs = dict(href=settings["DATABASE_SERVER"])
    if settings.get("DATABASE_ACCOUNT") and settings.get("DATABASE_PASSWORD"):
        kwargs["username"] = settings["DATABASE_ACCOUNT"]
        kwargs["password"] = settings["DATABASE_PASSWORD"]
    return couchdb2.Server(**kwargs)


def get_db():
    """Return the CouchDB2 handle for the CouchDB database.
    The named database must exist.
    """
    server = get_dbserver()
    name = settings["DATABASE_NAME"]
    try:
        return server[name]
    except couchdb2.NotFoundError:
        raise KeyError(f"CouchDB database '{name}' does not exist.")


def update_design_documents(db=None):
    "Ensure that all CouchDB design documents are up to date."
    if db is None:
        db = get_db()
    logger = logging.getLogger("publications")
    if db.put_design("account", ACCOUNT_DESIGN_DOC):
        logger.info("Updated 'account' CouchDB design document.")
    if db.put_design("blacklist", BLACKLIST_DESIGN_DOC):
        logger.info("Updated 'blacklist' CouchDB design document.")
    if db.put_design("journal", JOURNAL_DESIGN_DOC):
        logger.info("Updated 'journal' CouchDB design document.")
    if db.put_design("label", LABEL_DESIGN_DOC):
        logger.info("Updated 'label' CouchDB design document.")
    if db.put_design("log", LOG_DESIGN_DOC):
        logger.info("Updated 'log' CouchDB design document.")
    if db.put_design("publication", PUBLICATION_DESIGN_DOC):
        logger.info("Updated 'publication' CouchDB design document.")
    return db


def get_doc(db, designname, viewname, key):
    """Get the document with the given key from the given design view.
    Raise KeyError if not found.
    """
    view = db.view(designname, viewname, key=key, include_docs=True, reduce=False)
    result = list(view)
    if len(result) != 1:
        raise KeyError(f"{len(result)} items found")
    return result[0].doc


def get_docs(db, designname, viewname, key=None, last=None, **kwargs):
    """Get the list of documents using the given design view and
    the given key or interval.
    """
    if key is None:
        pass
    elif last is None:
        kwargs["key"] = key
    else:
        kwargs["startkey"] = key
        kwargs["endkey"] = last
    view = db.view(designname, viewname, include_docs=True, reduce=False, **kwargs)
    return [i.doc for i in view]


def get_count(db, designname, viewname, key=None):
    "Get the reduce value for the name view and the given key."
    if key is None:
        view = db.view(designname, viewname, reduce=True)
    else:
        view = db.view(designname, viewname, key=key, reduce=True)
    try:
        return list(view)[0].value
    except IndexError:
        return 0


def get_account(db, email):
    """Get the account identified by the email address.
    Raise KeyError if not found.
    """
    try:
        doc = get_doc(db, "account", "email", email.strip().lower())
    except KeyError:
        raise KeyError(f"no such account '{email}'")
    return doc


def get_publication(db, identifier):
    """Get the publication given its IUID, DOI or PMID.
    Raise KeyError if not found.
    """
    if not identifier:
        raise KeyError
    identifier = identifier.lower()
    try:
        doc = db[identifier]
    except couchdb2.NotFoundError:
        doc = None
        for viewname in ["doi", "pmid"]:
            try:
                doc = get_doc(db, "publication", viewname, identifier)
                break
            except KeyError:
                pass
        else:
            raise KeyError(f"no such publication '{identifier}'.")
    return doc


def get_researcher(db, identifier):
    """Get the researcher entity given its IUID or ORCID.
    Raise KeyError if not found.
    """
    if not identifier:
        raise KeyError
    try:
        doc = db[identifier.lower()]
    except couchdb2.NotFoundError:
        try:
            doc = get_doc(db, "researcher", "orcid", identifier)
        except KeyError:
            raise KeyError(f"no such researcher '{identifier}'.")
    return doc


def get_label(db, identifier):
    """Get the label document by its IUID or value.
    Raise KeyError if not found.
    """
    if not identifier:
        raise KeyError("no identifier provided")
    try:
        doc = db[identifier]
    except couchdb2.NotFoundError:
        identifier = utils.to_ascii(identifier).lower()
        try:
            doc = get_doc(db, "label", "normalized_value", identifier)
        except KeyError:
            raise KeyError(f"no such label '{identifier}'")
    return doc


def get_labels_years(db):
    """Return the years for which at least on label was active.
    Only if TEMPORAL_LABELS is set to True.
    """
    import publications.utils

    if not settings["TEMPORAL_LABELS"]:
        return []
    started = 100000
    ended = int(publications.utils.today().split("-")[0])
    for doc in get_docs(db, "label", "value"):
        try:
            started = min(started, int(doc.get("started")))
        except (ValueError, TypeError):
            pass
        try:
            ended = max(ended, int(doc.get("ended")))
        except (ValueError, TypeError):
            pass
    return list(range(started, ended + 1))


def get_blacklisted(db, identifier):
    """Get the blacklist document if the publication with
    the external identifier has been blacklisted.
    """
    if not identifier:
        return None
    for viewname in ["doi", "pmid"]:
        try:
            return get_doc(db, "blacklist", viewname, identifier)
        except KeyError:
            pass
    return None


ACCOUNT_DESIGN_DOC = {
    "views": {
        "api_key": {
            "map": """function (doc) {
  if (doc.publications_doctype !== 'account') return;
  if (!doc.api_key) return;
  emit(doc.api_key, doc.email);
}"""
        },
        "email": {
            "reduce": "_count",
            "map": """function (doc) {
  if (doc.publications_doctype !== 'account') return;
  emit(doc.email, null);
}""",
        },
        "label": {
            "map": """function (doc) {
  if (doc.publications_doctype !== 'account') return;
  for (var key in doc.labels) emit(doc.labels[key].toLowerCase(), doc.email);
}"""
        },
    }
}


BLACKLIST_DESIGN_DOC = {
    "views": {
        "doi": {
            "map": """function (doc) {
  if (doc.publications_doctype !== 'blacklist') return;
  if (doc.doi) emit(doc.doi, doc.title);
}"""
        },
        "pmid": {
            "map": """function (doc) {
  if (doc.publications_doctype !== 'blacklist') return;
  if (doc.pmid) emit(doc.pmid, doc.title);
}"""
        },
    }
}


JOURNAL_DESIGN_DOC = {
    "views": {
        "issn": {
            "map": """function (doc) {
  if (doc.publications_doctype !== 'journal') return;
  emit(doc.issn, doc.title);
}"""
        },
        "issn_l": {
            "map": """function (doc) {
  if (doc.publications_doctype !== 'journal' || !doc['issn-l']) return;
  emit(doc['issn-l'], doc.issn);
}"""
        },
        "title": {
            "map": """function (doc) {
  if (doc.publications_doctype !== 'journal') return;
  emit(doc.title, doc.issn);
}"""
        },
    }
}


LABEL_DESIGN_DOC = {
    "views": {
        "normalized_value": {
            "map": """function (doc) {
  if (doc.publications_doctype !== 'label') return;
  emit(doc.normalized_value, doc.value);
}"""
        },
        "value": {
            "reduce": "_count",
            "map": """function (doc) {
  if (doc.publications_doctype !== 'label') return;
  emit(doc.value, null);
}""",
        },
        "current": {
            "map": """function (doc) {
  if (doc.publications_doctype !== 'label') return;
  if (doc.ended) return;
  if (doc.secondary) return;
  emit(doc.started, doc.value);
}"""
        },
    }
}


LOG_DESIGN_DOC = {
    "views": {
        "account": {
            "map": """function (doc) {
  if (doc.publications_doctype !== 'log') return;
  if (!doc.account) return;
  emit([doc.account, doc.modified], null);
}"""
        },
        "doc": {
            "map": """function (doc) {
  if (doc.publications_doctype !== 'log') return;
  emit([doc.doc, doc.modified], null);
}"""
        },
        "modified": {
            "map": """function (doc) {
  if (doc.publications_doctype !== 'log') return;
   emit(doc.modified, null);
}"""
        },
    }
}


PUBLICATION_REMOVE = "".join(constants.SEARCH_REMOVE)
PUBLICATION_IGNORE = ",".join(["'%s':1" % i for i in constants.SEARCH_IGNORE])

PUBLICATION_DESIGN_DOC = {
    "views": {
        "author": {
            "map": """function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  var au, name;
  var length = doc.authors.length;
  for (var i=0; i<length; i++) {
    au = doc.authors[i];
    if (!au.family_normalized) continue;
    emit(au.family_normalized, null);
    if (au.initials_normalized) {
      name = au.family_normalized + ' ' + au.initials_normalized;
      emit(name, null);
    }
    if (au.given_normalized) {
      name = au.family_normalized + ' ' + au.given_normalized;
      emit(name, null);
    }
  }
}"""
        },
        "researcher": {
            "reduce": "_count",
            "map": """function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  var au;
  var length = doc.authors.length;
  for (var i=0; i<length; i++) {
    au = doc.authors[i];
    if (au.researcher) emit(au.researcher, au.family + ' ' + au.initials);
  }
}""",
        },
        "pmid": {
            "map": """function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (doc.pmid) emit(doc.pmid, null);
}"""
        },
        "doi": {
            "map": """function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (doc.doi) emit(doc.doi.toLowerCase(), null);
}"""
        },
        "no_pmid": {
            "map": """function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (!doc.pmid) emit(doc.published, null);
}"""
        },
        "no_doi": {
            "map": """function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (!doc.doi) emit(doc.published, null);
}"""
        },
        "epublished": {
            "map": """function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (!doc.epublished) return;
  emit(doc.epublished, null);
}"""
        },
        "first_published": {
            "map": """function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (!doc.published) return;
  if (doc.epublished) {
    if (doc.published < doc.epublished) {
      emit(doc.published, null);
    } else {
      emit(doc.epublished, null);
    };
  } else {
    emit(doc.published, null);
  };
}"""
        },
        "label_parts": {
            "map": """var REMOVE = /[%s]/g;
var IGNORE = {%s};
function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  var label, parts, part;
  for (var key in doc.labels) {
    label = doc.labels[key].toLowerCase();
    label = label.replace(REMOVE, ' ');
    parts = label.split(/\s+/);
    var length = parts.length;
    for (var i=0; i<length; i++) {
      part = parts[i];
      if (!part) continue;
      if (IGNORE[part]) continue;
      emit(part, null);
    }
  }
}"""
            % (PUBLICATION_REMOVE, PUBLICATION_IGNORE)
        },
        "issn": {
            "map": """function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (!doc.journal) return;
  if (doc.journal.issn) emit(doc.journal.issn, null);
  if (doc.journal['issn-l']) emit(doc.journal['issn-l'], null);
}"""
        },
        "journal": {
            "reduce": "_count",
            "map": """function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (!doc.journal) return;
  if (!doc.journal.title) return;
  emit(doc.journal.title, null);
}""",
        },
        "label": {
            "reduce": "_count",
            "map": """function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  for (var key in doc.labels) emit(key.toLowerCase(), null);
}""",
        },
        "no_label": {
            "map": """function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (Object.keys(doc.labels).length === 0) emit(doc.title, null);
}"""
        },
        "year": {
            "reduce": "_count",
            "map": """function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (!doc.published) return;
  var year = doc.published.split('-')[0];
  emit(year, null);
}""",
        },
        "modified": {
            "map": """function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  emit(doc.modified, null);
}"""
        },
        "notes": {
            "map": """var REMOVE = /[%s]/g;
var IGNORE = {%s};
function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  var notes = doc.notes.split(/\s+/);
  var note;
  var length = notes.length;
  for (var i=0; i<length; i++) {
    note = notes[i].toLowerCase();
    note = note.replace(REMOVE, '');
    if (!note) continue;
    if (IGNORE[note]) continue;
    emit(note, null);
  }
}"""
            % (PUBLICATION_REMOVE, PUBLICATION_IGNORE)
        },
        "published": {
            "map": """function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (!doc.published) return;
  emit(doc.published, null);
}"""
        },
        "title": {
            "map": """var REMOVE = /[%s]/g;
var IGNORE = {%s};
function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  var words = doc.title.split(/\s+/);
  var word;
  var length = words.length;
  for (var i=0; i<length; i++) {
    word = words[i].toLowerCase();
    word = word.replace(REMOVE, '');
    if (!word) continue;
    if (IGNORE[word]) continue;
    emit(word, null);
  }
}"""
            % (PUBLICATION_REMOVE, PUBLICATION_IGNORE)
        },
        "xref": {
            "map": """function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  var xref;
  var length = doc.xrefs.length;
  for (var i=0; i<length; i++) {
    xref = doc.xrefs[i];
    if (!xref.db) continue;
    if (!xref.key) continue;
    emit(xref.key, xref.db);
  }
}"""
        },
    }
}
