/* Index publication document by journal title to allow count.
   Value: 1.
*/
function(doc) {
    if (doc.publications_doctype !== 'publication') return;
    if (!doc.journal) return;
    if (!doc.journal.title) return;
    emit(doc.journal.title, 1);
}
