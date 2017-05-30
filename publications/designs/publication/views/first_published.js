/* Index publication document by first published timestamp.
   Value: title.
*/
function(doc) {
    if (doc.publications_doctype !== 'publication') return;
    if (!doc.verified) return;
    if (!doc.published) return;
    if (doc.epublished) {
	if (doc.published < doc.epublished) {
	    emit(doc.published, doc.title);
	} else {
	    emit(doc.epublished, doc.title);
	};
    } else {
	emit(doc.published, doc.title);
    };
}
