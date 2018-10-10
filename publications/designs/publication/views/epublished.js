/* Index publication document by epublished timestamp.
   Value: title.
*/
function(doc) {
    if (doc.publications_doctype !== 'publication') return;
    if (!doc.epublished) return;
    emit(doc.epublished, doc.title);
}
