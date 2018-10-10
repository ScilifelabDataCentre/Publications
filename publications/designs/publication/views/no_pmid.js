/* Index publication document lacking PMID by published date.
   Value: title.
*/
function(doc) {
    if (doc.publications_doctype !== 'publication') return;
    if (!doc.pmid) emit(doc.published, doc.title);
}
