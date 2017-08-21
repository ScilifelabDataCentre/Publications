/* Index unverified publication document by label lowercase value.
   Value: title.
*/
function(doc) {
    if (doc.publications_doctype !== 'publication') return;
    if (doc.verified) return;
    var key;
    for (key in doc.labels) emit(key.toLowerCase(), doc.title);
}
