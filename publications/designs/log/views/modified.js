/* Log documents indexed by modified.
   Value: null.
*/
function(doc) {
    if (doc.publications_doctype !== 'log') return;
    emit(doc.modified, null);
}
