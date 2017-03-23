/* Index label document by value.
   Value: null.
*/
function(doc) {
    if (doc.publications_doctype !== 'label') return;
    emit(doc.value.toLowerCase(), null);
}
