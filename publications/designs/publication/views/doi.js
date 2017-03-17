/* Index publication document by DOI.
   Value: title.
*/
function(doc) {
    if (doc.publications_doctype !== 'publication') return;
    if (doc.doi) emit(doc.doi, doc.title);
}
