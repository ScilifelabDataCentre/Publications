/* Publications
   Index publication document by published timestamp.
   Value: title.
*/
function(doc) {
    if (doc.publications_doctype !== 'publication') return;
    if (doc.doi) emit(doc.published, doc.title);
}
