/* Index unverified publication document by label value.
   Value: title.
*/
function(doc) {
    if (doc.publications_doctype !== 'publication') return;
    if (doc.verified) return;
    for (var i in doc.labels) emit(doc.labels[i], doc.title);
}
