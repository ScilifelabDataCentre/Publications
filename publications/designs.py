"CouchDB design documents (view index definitions)."

import logging

from publications import constants

REMOVE = "".join(constants.SEARCH_REMOVE)
IGNORE = ",".join(["'%s':1" % i for i in constants.SEARCH_IGNORE])

DESIGNS = dict(

    account=dict(
        api_key=dict(map=       # account/api_key
"""function (doc) {
  if (doc.publications_doctype !== 'account') return;
  if (!doc.api_key) return;
  emit(doc.api_key, doc.email);
}"""),
        email=dict(reduce="_count", # account/email
                   map=         
"""function (doc) {
  if (doc.publications_doctype !== 'account') return;
  emit(doc.email, null);
}"""),
        label=dict(map=         # account/label
"""function (doc) {
  if (doc.publications_doctype !== 'account') return;
  for (var key in doc.labels) emit(doc.labels[key].toLowerCase(), doc.email);
}""")),

    blacklist=dict(
        doi=dict(map=           # blacklist/doi
"""function (doc) {
  if (doc.publications_doctype !== 'blacklist') return;
  if (doc.doi) emit(doc.doi, doc.title);
}"""),
        pmid=dict(map=          # blacklist/pmid
"""function (doc) {
  if (doc.publications_doctype !== 'blacklist') return;
  if (doc.pmid) emit(doc.pmid, doc.title);
}""")),

    journal=dict(
        issn=dict(map=          # journal/issn
"""function (doc) {
  if (doc.publications_doctype !== 'journal') return;
  emit(doc.issn, doc.title);
}"""),
        issn_l=dict(map=          # journal/issn_l
"""function (doc) {
  if (doc.publications_doctype !== 'journal' || !doc['issn-l']) return;
  emit(doc['issn-l'], doc.issn);
}"""),
        title=dict(map=         # journal/title
"""function (doc) {
  if (doc.publications_doctype !== 'journal') return;
  emit(doc.title, doc.issn);
}""")),

    label=dict(
        normalized_value=dict(map= # label/normalized_value
"""function (doc) {
  if (doc.publications_doctype !== 'label') return;
  emit(doc.normalized_value, doc.value);
}"""),
        value=dict(reduce="_count", # label/value
                   map=
"""function (doc) {
  if (doc.publications_doctype !== 'label') return;
  emit(doc.value, null);
}"""),
        current=dict(map=       # label/current
"""function (doc) {
  if (doc.publications_doctype !== 'label') return;
  if (doc.ended) return;
  emit(doc.started, doc.value);
}""")),

    log=dict(
        account=dict(map=       # log/account
"""function (doc) {
  if (doc.publications_doctype !== 'log') return;
  if (!doc.account) return;
  emit([doc.account, doc.modified], null);
}"""),
        doc=dict(map=           # log/doc
"""function (doc) {
  if (doc.publications_doctype !== 'log') return;
  emit([doc.doc, doc.modified], null);
}"""),
        modified=dict(map=
"""function (doc) {
  if (doc.publications_doctype !== 'log') return;
   emit(doc.modified, null);
}""")),

    publication=dict(
        author=dict(map=        # publication/author
"""function (doc) {
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
}"""),
        researcher=dict(reduce="_count", # publication/researcher
                        map=
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  var au;
  var length = doc.authors.length;
  for (var i=0; i<length; i++) {
    au = doc.authors[i];
    if (au.researcher) emit(au.researcher, au.family + ' ' + au.initials);
  }
}"""),
        pmid=dict(map=          # publication/pmid
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (doc.pmid) emit(doc.pmid, null);
}"""),
        doi=dict(map=           # publication/doi
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (doc.doi) emit(doc.doi.toLowerCase(), null);
}"""),
        no_pmid=dict(map=       # publication/no_pmid
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (!doc.pmid) emit(doc.published, null);
}"""),
        no_doi=dict(map=        # publication/no_doi
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (!doc.doi) emit(doc.published, null);
}"""),
        epublished=dict(map=    # publication/epublished
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (!doc.epublished) return;
  emit(doc.epublished, null);
}"""),
        first_published=dict(map= # publication/first_published
"""function (doc) {
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
}"""),
        label_parts=dict(map=   # publication/label_parts
"""var REMOVE = /[%s]/g;
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
}""" % (REMOVE, IGNORE)),
        issn=dict(map=          # publication/issn (and issn-l)
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (!doc.journal) return;
  if (doc.journal.issn) emit(doc.journal.issn, null);
  if (doc.journal['issn-l']) emit(doc.journal['issn-l'], null);
}"""),
        journal=dict(reduce="_count", # publication/journal
                     map=
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (!doc.journal) return;
  if (!doc.journal.title) return;
  emit(doc.journal.title, null);
}"""),
        label=dict(reduce="_count", # publication/label
                   map=
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  for (var key in doc.labels) emit(key.toLowerCase(), null);
}"""),
        no_label=dict(map=      # publication/no_label
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (Object.keys(doc.labels).length === 0) emit(doc.title, null);
}"""),
        year=dict(reduce="_count", # publication/year
                  map=
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (!doc.published) return;
  var year = doc.published.split('-')[0];
  emit(year, null);
}"""),
        modified=dict(map=
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  emit(doc.modified, null);
}"""),
        notes=dict(map=         # publication/notes
"""var REMOVE = /[%s]/g;
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
}""" % (REMOVE, IGNORE)),
        published=dict(map=     # publication/published
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (!doc.published) return;
  emit(doc.published, null);
}"""),
        no_published=dict(map=     # publication/no_published
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (doc.published) return;
  emit(doc.modified, null);
}"""),
        title=dict(map=         # publication/title
"""var REMOVE = /[%s]/g;
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
}""" % (REMOVE, IGNORE)),
        xref=dict(map=          # publication/xref
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  var xref;
  var length = doc.xrefs.length;
  for (var i=0; i<length; i++) {
    xref = doc.xrefs[i];
    if (!xref.db) continue;
    if (!xref.key) continue;
    emit(xref.key, xref.db);
  }
}"""),
    ),

    researcher=dict(
        orcid=dict(map=         # researcher/orcid
"""function (doc) {
  if (doc.publications_doctype !== 'researcher') return;
  if (doc.orcid) emit(doc.orcid, doc.family + ' ' + doc.initials);
}"""),
        family=dict(map=        # researcher/family
"""function (doc) {
  if (doc.publications_doctype !== 'researcher') return;
  emit(doc.family_normalized, doc.family + ' ' + doc.initials);
}"""),
        name=dict(reduce="_count", # researcher/name
                  map=
"""function (doc) {
  if (doc.publications_doctype !== 'researcher') return;
  emit(doc.family_normalized + ' ' + doc.initials_normalized, null);
}"""),

    ),
)


def load_design_documents(db):
    "Load the design documents (view index definitions)."
    for designname, views in DESIGNS.items():
        if db.put_design(designname, {"views": views}, rebuild=True):
            logging.info("loaded design %s", designname)
