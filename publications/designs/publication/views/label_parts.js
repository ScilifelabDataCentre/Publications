/* Index publication documents by label lowercase parts, ignoring short words.
   Value: null.
*/

/* Must be kept in sync with search.py */
var REMOVE = /[-\.:,?()$]/g;
var IGNORE = {
    'a': 1,
    'an': 1,
    'and': 1,
    'are': 1,
    'as': 1,
    'at': 1,
    'but': 1,
    'by': 1,
    'can': 1,
    'for': 1,
    'from': 1,
    'into': 1,
    'in': 1,
    'is': 1,
    'of': 1,
    'on': 1,
    'or': 1,
    'that': 1,
    'the': 1,
    'to': 1,
    'using': 1,
    'with': 1
};

function(doc) {
    if (doc.publications_doctype !== 'publication') return;
    if (!doc.verified) return;
    var label, parts, part;
    for (var i in doc.labels) {
	label = doc.labels[i].toLowerCase();
	label = label.replace(REMOVE, ' ');
	parts = label.split(/\s+/);
	for (var j in parts) {
	    part = parts[j];
	    if (!part) continue;
	    if (IGNORE[part]) continue;
	    emit(part, null);
	}
    }
}
