/* Index unverified publication document by published.
   Value: title.
*/
function(doc) {
    if (doc.publications_doctype !== 'publication') return;
    if (doc.verified) return;
    emit(doc.published, doc.title);
}
