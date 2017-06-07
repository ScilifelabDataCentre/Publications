/* Index blacklisted document by PMID.
   Value: title.
*/
function(doc) {
    if (doc.publications_doctype !== 'blacklist') return;
    if (doc.pmid) emit(doc.pmid, doc.title);
}
