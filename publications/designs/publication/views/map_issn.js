/* Index publication document by journal ISSN to allow count.
   Value: 1.
*/
function(doc) {
    if (doc.publications_doctype !== 'publication') return;
    if (!doc.journal) return;
    if (!doc.journal.issn) return;
    emit(doc.journal.issn, 1);
}
