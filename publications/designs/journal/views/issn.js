/* Index journal document by ISSN.
   Value: title.
*/
function(doc) {
    if (doc.publications_doctype !== 'journal') return;
    emit(doc.issn, doc.title);
}
