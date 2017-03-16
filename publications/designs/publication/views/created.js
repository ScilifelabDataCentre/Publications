/* Publications
   Index publication document by created timestamp.
   Value: title.
*/
function(doc) {
    if (doc.publications_doctype !== 'publication') return;
    if (doc.doi) emit(doc.created, doc.title);
}
