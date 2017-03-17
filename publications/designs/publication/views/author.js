/* Index publication document by author's normalized names.
   Value: null.
*/
function(doc) {
    if (doc.publications_doctype !== 'publication') return;
    var au, name;
    for (var i in doc.authors) {
	au = doc.authors[i];
	if (!au.family_normalized) continue;
	emit(au.family_normalized.toLowerCase(), null);
	if (au.initials_normalized) {
	    name = au.family_normalized + ' ' + au.initials_normalized;
	    emit(name.toLowerCase(), null);
	}
	if (au.given_normalized) {
	    name = au.family_normalized + ' ' + au.given_normalized;
	    emit(name.toLowerCase(), null);
	}
    }
}
