/* Log documents indexed by account and modified.
   Value: null.
*/
function(doc) {
    if (doc.publications_doctype !== 'log') return;
    if (!doc.account) return;
    emit([doc.account, doc.modified], null);
}
