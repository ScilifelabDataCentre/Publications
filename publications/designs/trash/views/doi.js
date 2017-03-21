/* Index trash document by DOI.
   Value: title.
*/
function(doc) {
    if (doc.publications_doctype !== 'trash') return;
    if (doc.doi) emit(doc.doi, doc.title);
}
