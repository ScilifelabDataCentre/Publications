/* Index publication document by label value.
   Value: null.
*/
function(doc) {
    if (doc.publications_doctype !== 'publication') return;
    for (var i in doc.labels) {
	emit(doc.labels[i], null);
    }
}
