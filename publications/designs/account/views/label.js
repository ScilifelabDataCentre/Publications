/* Account documents indexed by label lowercase value.
   Value: email.
*/
function(doc) {
    if (doc.publications_doctype !== 'account') return;
    for (var key in doc.labels) emit(doc.labels[key].toLowerCase(), doc.email);
}
