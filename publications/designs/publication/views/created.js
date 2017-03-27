/* Index publication document by created timestamp.
   Value: title.
*/
function(doc) {
    if (doc.publications_doctype !== 'publication') return;
    if (!doc.verified) return;
    emit(doc.created, doc.title);
}
