/* Index unverified publication document by PMID.
   Value: title.
*/
function(doc) {
    if (doc.publications_doctype !== 'publication') return;
    if (doc.verified) return;
    if (doc.pmid) emit(doc.pmid, doc.title);
}
