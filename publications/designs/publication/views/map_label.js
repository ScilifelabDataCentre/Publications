/* Index publication document by label lowercase value to allow count.
   Value: 1.
*/
function(doc) {
    if (doc.publications_doctype !== 'publication') return;
    for (var key in doc.labels) emit(key.toLowerCase(), 1);
}
