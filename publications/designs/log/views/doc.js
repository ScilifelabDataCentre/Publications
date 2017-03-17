/* Log documents indexed by doc id and modified.
   Value: null.
*/
function(doc) {
    if (doc.publications_doctype !== 'log') return;
    emit([doc.doc, doc.modified], null);
}
