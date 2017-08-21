/* Index publication document by label lowercase value to allow count.
   Value: 1.
*/
function(doc) {
    if (doc.publications_doctype !== 'publication') return;
    if (!doc.verified) return;
    for (var key in doc.labels) emit(key.toLowerCase(), 1);
}
