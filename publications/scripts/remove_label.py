"""Remove a specified label from all publications.
Does not delete the label itself.
"""

from publications import utils
from publications.publication import PublicationSaver


def remove_label(db, label):
    if not label:
        raise ValueError('no label given')
    view = db.view('label/value', key=label)
    if len(view) == 0:
        raise ValueError("label %s does not exist" % label)
    
    view = db.view('publication/modified', include_docs=True)
    for item in view:
        if label in item.doc['labels']:
            with PublicationSaver(doc=item.doc, db=db) as saver:
                labels = item.doc['labels'].copy()
                labels.pop(label)
                saver['labels'] = labels
            print(item.doc['_id'], item.doc['labels'])


if __name__ == '__main__':
    parser = utils.get_command_line_parser(
        'Remove a label from all publications.')
    parser.add_argument('--label', action='store', dest='label',
                        default=None, help='label to remove')
    args = parser.parse_args()
    utils.load_settings(filepath=args.settings)
    db = utils.get_db()
    remove_label(db, args.label)
