/* Account documents indexed by email address.
   Value: first and last names.
*/
function(doc) {
    if (doc.publications_doctype !== 'account') return;
    emit(doc.email, null);
}
