/* Index publication document by publication year to allow count.
   Value: 1.
*/
function(doc) {
    if (doc.publications_doctype !== 'publication') return;
    if (!doc.published) return;
    var year = doc.published.split('-')[0];
    emit(year, 1);
}
