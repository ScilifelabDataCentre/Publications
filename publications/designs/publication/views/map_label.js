/* Index publication document by label value to allow count.
   Value: 1.
*/
function(doc) {
    if (doc.publications_doctype !== 'publication') return;
    for (var i in doc.labels) emit(doc.labels[i], 1);
}
