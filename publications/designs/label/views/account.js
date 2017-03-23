/* Index label document by account.
   Value: value.
*/
function(doc) {
    if (doc.publications_doctype !== 'label') return;
    for (var i in doc.accounts) {
	emit(doc.accounts[i], doc.value);
    }
}
