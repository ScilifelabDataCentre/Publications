/* Index publication document by journal title.
   Value: null.
*/
function(doc) {
    if (doc.publications_doctype !== 'publication') return;
    if (!doc.journal) return;
    if (!doc.journal.title) return;
    emit(doc.journal.title, null);
}
