"Add a label to publications given by IUID, DOI or PMID."

from publications import utils
from publications.publication import PublicationSaver


def add_label_to_publications(db, label, qualifier, identifiers):
    if not label:
        raise ValueError('no new label given')
    if not qualifier:
        raise ValueError('no new qualifier given')
    if not identifiers:
        raise ValueError('no identifiers given')
    view = db.view('label/value', key=label)
    if len(view) == 0:
        raise ValueError("label %s does not exist" % label)

    count = 0
    errors = []
    for identifier in identifiers:
        try:
            publ = utils.get_publication(db, identifier)
        except KeyError as error:
            errors.append(str(error))
        else:
            if label not in publ['labels']:
                with PublicationSaver(doc=publ, db=db) as saver:
                    labels = publ['labels'].copy()
                    labels[label] = qualifier
                    saver['labels'] = labels
                count += 1
    print("Label '%s/%s' added to %i publications" % (label, qualifier, count))
    for error in errors:
        print(error)


if __name__ == '__main__':
    parser = utils.get_command_line_parser(
        'Add a label to all publications in a list.')
    parser.add_argument('--label', action='store', dest='label',
                        default=None, help='label to add')
    parser.add_argument('--qualifier', action='store', dest='qualifier',
                        default=None, help='qualifier of label to add')
    parser.add_argument('--file', action='store', dest='idfile',
                        metavar='IDFILE',
                        help='path to file containing publication identifiers')
    args = parser.parse_args()
    utils.load_settings(filepath=args.settings)
    db = utils.get_db()
    identifiers = []
    with open(args.idfile) as infile:
        for line in infile:
            line = line.strip()
            if line: identifiers.append(line)
    print(len(identifiers), 'identifiers')
    add_label_to_publications(db, args.label, args.qualifier, identifiers)
