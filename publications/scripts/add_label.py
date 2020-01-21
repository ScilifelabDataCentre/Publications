"Add a label to all publications having other label(s). Both must exist."

from __future__ import print_function

from publications import utils
from publications.publication import PublicationSaver


qualifier_lookup = {'Collaborative': 3,
                    'Technology development': 2,
                    'Service': 1}

def add_label(db, new_label, existing_labels):
    if not new_label:
        raise ValueError('no new label given')
    if len(existing_labels) == 0:
        raise ValueError('no existing labels given')
    view = db.view('label/value', key=new_label)
    if len(view) == 0:
        raise ValueError("label %s does not exist" % new_label)
    for existing_label in existing_labels:
        view = db.view('label/value', key=existing_label)
        if len(view) == 0:
            raise ValueError("label %s does not exist" % existing_label)
    
    view = db.view('publication/modified', include_docs=True)
    for item in view:
        qualifier = None
        for existing_label in existing_labels:
            if existing_label in item.doc['labels']:
                if qualifier is None:
                    qualifier = item.doc['labels'][existing_label]
                else:
                    qualifier = max(qualifier,
                                    item.doc['labels'][existing_label])
        if qualifier is not None:
            for k, v in qualifier_lookup.items():
                if v == qualifier:
                    qualifier = k
                    break
            with PublicationSaver(doc=item.doc, db=db) as saver:
                labels = item.doc['labels'].copy()
                labels[new_label] = qualifier
                saver['labels'] = labels
            print(item.doc['_id'], item.doc['labels'], qualifier)


if __name__ == '__main__':
    parser = utils.get_command_line_parser(
        'Add a label to all publications having other label(s).')
    parser.add_argument('--new', action='store', dest='new',
                        default=None, help='new label to add')
    parser.add_argument('--existing', action='append', dest='existing',
                        default=None, help='existing label')
    args = parser.parse_args()
    utils.load_settings(filepath=args.settings)
    db = utils.get_db()
    add_label(db, args.new, args.existing)
