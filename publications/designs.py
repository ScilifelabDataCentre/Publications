"CouchDB design documents (view index definitions)."

import logging

import couchdb

from . import constants

REMOVE = ''.join(constants.SEARCH_REMOVE)
IGNORE = ','.join(["'%s':1" % i for i in constants.SEARCH_IGNORE])

DESIGNS = dict(

    account=dict(
        api_key=dict(map=       # account/api_key
"""function (doc) {
  if (doc.publications_doctype !== 'account') return;
  if (!doc.api_key) return;
  emit(doc.api_key, doc.email);
}"""),
        email=dict(map=         # account/email
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
        title=dict(map=         # journal/title
"""function (doc) {
  if (doc.publications_doctype !== 'journal') return;
  emit(doc.title, doc.issn);
}""")),

    label=dict(
        normalized_value=dict(map= # label/normalized_value
"""function (doc) {
  if (doc.publications_doctype !== 'label') return;
  emit(doc.normalized_value, null);
}"""),
        value=dict(map=         # label/value
"""function (doc) {
  if (doc.publications_doctype !== 'label') return;
  emit(doc.value, null);
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
        acquired=dict(map=      # publication/acquired
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (!doc.acquired) return;
  emit(doc.acquired.account, null);
}"""),
        author=dict(map=        # publication/author
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  var au, name;
  var length = doc.authors.length;
  for (var i=0; i<length; i++) {
    au = doc.authors[i];
    if (!au.family_normalized) continue;
    emit(au.family_normalized.toLowerCase(), null);
    if (au.initials_normalized) {
      name = au.family_normalized + ' ' + au.initials_normalized;
      emit(name.toLowerCase(), null);
    }
    if (au.given_normalized) {
      name = au.family_normalized + ' ' + au.given_normalized;
      emit(name.toLowerCase(), null);
    }
  }
}"""),
        doi=dict(map=           # publication/doi
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (doc.doi) emit(doc.doi.toLowerCase(), doc.title);
}"""),
        epublished=dict(map=    # publication/epublished
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (!doc.epublished) return;
  emit(doc.epublished, doc.title);
}"""),
        first_published=dict(map= # publication/first_published
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (!doc.published) return;
  if (doc.epublished) {
    if (doc.published < doc.epublished) {
      emit(doc.published, doc.title);
    } else {
      emit(doc.epublished, doc.title);
    };
  } else {
    emit(doc.published, doc.title);
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
        issn=dict(reduce='_sum', # publication/issn
                  map=
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (!doc.journal) return;
  if (!doc.journal.issn) return;
  emit(doc.journal.issn, 1);
}"""),
        journal=dict(reduce='_sum', # publication/journal
                     map=
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (!doc.journal) return;
  if (!doc.journal.title) return;
  emit(doc.journal.title, 1);
}"""),
        label=dict(reduce="_sum", # publication/label
                   map=
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  for (var key in doc.labels) emit(key.toLowerCase(), 1);
}"""),
        year=dict(reduce="_sum", # publication/year
                  map=
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (!doc.published) return;
  var year = doc.published.split('-')[0];
  emit(year, 1);
}"""),
        modified=dict(map=      # publication/modified
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  emit(doc.modified, doc.title);
}"""),
        no_doi=dict(map=        # publication/no_doi
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (!doc.doi) emit(doc.published, doc.title);
}"""),
        no_pmid=dict(map=       # publication/no_pmid
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (!doc.pmid) emit(doc.published, doc.title);
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
        pmid=dict(map=          # publication/pmid
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (doc.pmid) emit(doc.pmid, doc.title);
}"""),
        published=dict(map=     # publication/published
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (!doc.published) return;
  emit(doc.published, doc.title);
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
)


def load_design_documents(db):
    "Load the design documents (view index definitions)."
    for entity, designs in list(DESIGNS.items()):
        updated = update_design_document(db, entity, designs)
        if updated:
            for view in designs:
                name = "%s/%s" % (entity, view)
                logging.info("regenerating index for view %s" % name)
                list(db.view(name, limit=10))

def update_design_document(db, design, views):
    "Update the design document (view index definition)."
    docid = "_design/%s" % design
    try:
        doc = db[docid]
    except couchdb.http.ResourceNotFound:
        logging.info("loading design document %s", docid)
        db.save(dict(_id=docid, views=views))
        return True
    else:
        if doc['views'] != views:
            doc['views'] = views
            logging.info("updating design document %s", docid)
            db.save(doc)
            return True
        return False

def regenerate_indexes(db):
    "Regenerate all indexes."
    for entity, designs in list(DESIGNS.items()):
        for view in designs:
            name = "%s/%s" % (entity, view)
            logging.info("regenerating index for view %s" % name)
            list(db.view(name, limit=10))
