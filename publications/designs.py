"CouchDB design documents (view index definitions)."

import logging

import couchdb

from . import constants


DESIGNS = dict(

    account=dict(
        api_key=dict(map=
"""function (doc) {
  if (doc.publications_doctype !== 'account') return;
  if (!doc.api_key) return;
  emit(doc.api_key, doc.email);
}"""),
        email=dict(map=
"""function (doc) {
  if (doc.publications_doctype !== 'account') return;
  emit(doc.email, null);
}"""),
        label=dict(map=
"""function (doc) {
  if (doc.publications_doctype !== 'account') return;
  for (var key in doc.labels) emit(doc.labels[key].toLowerCase(), doc.email);
}""")),

    blacklist=dict(
        doi=dict(map=
"""function (doc) {
  if (doc.publications_doctype !== 'blacklist') return;
  if (doc.doi) emit(doc.doi, doc.title);
}"""),
        pmid=dict(map=
"""function (doc) {
  if (doc.publications_doctype !== 'blacklist') return;
  if (doc.pmid) emit(doc.pmid, doc.title);
}""")),
    journal=dict(
        issn=dict(map=
"""function (doc) {
  if (doc.publications_doctype !== 'journal') return;
  emit(doc.issn, doc.title);
}"""),
        title=dict(map=
"""function (doc) {
  if (doc.publications_doctype !== 'journal') return;
  emit(doc.title, doc.issn);
}""")),

    label=dict(
        normalized_value=dict(map=
"""function (doc) {
  if (doc.publications_doctype !== 'label') return;
  emit(doc.normalized_value, null);
}"""),
        value=dict(map=
"""function (doc) {
  if (doc.publications_doctype !== 'label') return;
  emit(doc.value, null);
}""")),

    log=dict(
        account=dict(map=
"""function (doc) {
  if (doc.publications_doctype !== 'log') return;
  if (!doc.account) return;
  emit([doc.account, doc.modified], null);
}"""),
        doc=dict(map=
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
        acquired=dict(map=
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (!doc.acquired) return;
  emit(doc.acquired.account, null);
}"""),
        author=dict(map=
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  var au, name;
  for (var i in doc.authors) {
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
        created=dict(map=
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  emit(doc.created, doc.title);
}"""),
        doi=dict(map=
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (doc.doi) emit(doc.doi.toLowerCase(), doc.title);
}"""),
        epublished=dict(map=
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (!doc.epublished) return;
  emit(doc.epublished, doc.title);
}"""),
        first_published=dict(map=
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
        label_parts=dict(map=
"""var REMOVE = /[%s]/g;
var IGNORE = {%s};
function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  var label, parts, part;
  for (var i in doc.labels) {
    label = doc.labels[i].toLowerCase();
    label = label.replace(REMOVE, ' ');
    parts = label.split(/\s+/);
    for (var j in parts) {
      part = parts[j];
      if (!part) continue;
      if (IGNORE[part]) continue;
        emit(part, null);
    }
  }
}""" % (''.join(constants.SEARCH_REMOVE),
        ','.join(["'%s':1" % i for i in constants.SEARCH_IGNORE]))),
        issn=dict(reduce='_sum',
                  map=
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (!doc.journal) return;
  if (!doc.journal.issn) return;
  emit(doc.journal.issn, 1);
}"""),
        journal=dict(reduce='_sum',
                     map=
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (!doc.journal) return;
  if (!doc.journal.title) return;
  emit(doc.journal.title, 1);
}"""),
        label=dict(reduce="_sum",
                   map=
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  for (var key in doc.labels) emit(key.toLowerCase(), 1);
}"""),
        year=dict(reduce="_sum",
                  map=
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (!doc.published) return;
  var year = doc.published.split('-')[0];
  emit(year, 1);
}"""),
        modified=dict(map=
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  emit(doc.modified, doc.title);
}"""),
        no_doi=dict(map=
"""function (doc) {
  if (doc.publications_doctype !== 'publication') return;
  if (!doc.doi) emit(doc.published, doc.title);
}"""),
        no_pmid=dict(map=
"""function (doc) {
    if (doc.publications_doctype !== 'publication') return;
    if (!doc.pmid) emit(doc.published, doc.title);
}"""),
        notes=dict(map=
"""var REMOVE = /[%s]/g;
var IGNORE = {%s};
function (doc) {
    if (doc.publications_doctype !== 'publication') return;
    var notes = doc.notes.split(/\s+/);
    var note;
    for (var i in notes) {
	note = notes[i].toLowerCase();
	note = note.replace(REMOVE, '');
	if (!note) continue;
	if (IGNORE[note]) continue;
	emit(note, null);
    }
}""" % (''.join(constants.SEARCH_REMOVE),
        ','.join(["'%s':1" % i for i in constants.SEARCH_IGNORE]))),
        pmid=dict(map=
"""function (doc) {
    if (doc.publications_doctype !== 'publication') return;
    if (doc.pmid) emit(doc.pmid, doc.title);
}"""),
        published=dict(map=
"""function (doc) {
    if (doc.publications_doctype !== 'publication') return;
    if (!doc.published) return;
    emit(doc.published, doc.title);
}"""),
        title=dict(map=
"""var REMOVE = /[%s]/g;
var IGNORE = {%s};
function (doc) {
    if (doc.publications_doctype !== 'publication') return;
    var words = doc.title.split(/\s+/);
    var word;
    for (var i in words) {
	word = words[i].toLowerCase();
	word = word.replace(REMOVE, '');
	if (!word) continue;
	if (IGNORE[word]) continue;
	emit(word, null);
    }
}""" % (''.join(constants.SEARCH_REMOVE),
        ','.join(["'%s':1" % i for i in constants.SEARCH_IGNORE]))),
        )
    )


def load_design_documents(db):
    "Load the design documents (view index definitions)."
    for entity, designs in DESIGNS.items():
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
