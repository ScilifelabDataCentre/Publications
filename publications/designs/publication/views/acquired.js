/* Index acquired publication document by account.
   Value: null.
*/
function(doc) {
    if (doc.publications_doctype !== 'publication') return;
    if (!doc.acquired) return;
    emit(doc.acquired.account, null);
}
