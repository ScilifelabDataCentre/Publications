/* Index publication document by modified timestamp.
   Value: title.
*/
function(doc) {
    if (doc.publications_doctype !== 'publication') return;
    if (!doc.verified) return;
    emit(doc.modified, doc.title);
}
