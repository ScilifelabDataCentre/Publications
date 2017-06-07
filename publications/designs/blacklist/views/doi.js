/* Index blacklisted document by DOI.
   Value: title.
*/
function(doc) {
    if (doc.publications_doctype !== 'blacklist') return;
    if (doc.doi) emit(doc.doi, doc.title);
}
