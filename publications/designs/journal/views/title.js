/* Index journal document by title.
   Value: ISSN.
*/
function(doc) {
    if (doc.publications_doctype !== 'journal') return;
    emit(doc.title, doc.issn);
}
