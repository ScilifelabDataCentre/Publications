/* Index label document by normalized value.
   Value: null.
*/
function(doc) {
    if (doc.publications_doctype !== 'label') return;
    emit(doc.value_normalized, null);
}
