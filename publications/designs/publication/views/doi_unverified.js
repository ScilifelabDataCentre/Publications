/* Index unverified publication document by DOI.
   Value: title.
*/
function(doc) {
    if (doc.publications_doctype !== 'publication') return;
    if (doc.verified) return;
    if (doc.doi) emit(doc.doi, doc.title);
}
