/* Index trash document by PMID.
   Value: title.
*/
function(doc) {
    if (doc.publications_doctype !== 'trash') return;
    if (doc.pmid) emit(doc.pmid, doc.title);
}
