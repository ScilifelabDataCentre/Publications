/* Index publication document lacking DOI by published date.
   Value: title.
*/
function(doc) {
    if (doc.publications_doctype !== 'publication') return;
    if (!doc.verified) return;
    if (!doc.doi) emit(doc.published, doc.title);
}
