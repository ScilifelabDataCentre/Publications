/* Account documents indexed by label.
   Value: email.
*/
function(doc) {
    if (doc.publications_doctype !== 'account') return;
    for (var i in doc.labels) emit(doc.labels[i], doc.email);
}
