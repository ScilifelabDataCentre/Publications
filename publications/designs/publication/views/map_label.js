/* Index publication document by label value to allow count.
   Value: 1.
*/
function(doc) {
    if (doc.publications_doctype !== 'publication') return;
    if (!doc.verified) return;
    var key;
    for (key in doc.labels) emit(key, 1);
}
