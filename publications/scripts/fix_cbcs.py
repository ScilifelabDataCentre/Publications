# coding: utf-8
"Add CBCS label for all CBCS facilities."

from __future__ import print_function

import time

from publications import constants
from publications import settings
from publications import utils
from publications.publication import PublicationSaver

def get_args():
    parser = utils.get_command_line_parser(
        "Scrap all labels for CBCS facilities and replace by it.")
    return parser.parse_args()

def add_cbcs_label(db):
    "Add CBCS label for all CBCS facilities."
    qual_lookup = dict([(v,k) for k,v
                        in enumerate(settings['SITE_LABEL_QUALIFIERS'])])
    CBCS = 'Chemical Biology Consortium Sweden (CBCS)'
    OLD = [u'Laboratories for Chemical Biology at Karolinska Institutet (LCBKI)',
           u'Laboratories for Chemical Biology Umeå (LCBU)',
           u'Uppsala Drug Optimization and Pharmaceutical Profiling (UDOPP)']
    for label in OLD:
        print('-----', label)
        for row in db.view('publication/label', 
                           key=label.lower(),
                           reduce=False,
                           include_docs=True):
            doc = row.doc
            print(doc['title'])
            with PublicationSaver(doc=doc, db=db) as saver:
                labels = doc['labels'].copy()
                qual = labels[label]
                try:
                    qual = settings['SITE_LABEL_QUALIFIERS']\
                           [max(qual_lookup[qual], qual_lookup[labels[CBCS]])]
                except KeyError:
                    pass
                labels[CBCS] = qual
                saver['labels'] = labels
                notes = doc.get('notes')
                if notes:
                    notes += u'\n' + label
                else:
                    notes = label
                saver['notes'] = notes
                # Old label will be deleted eventually, so keep a record.


if __name__ == '__main__':
    args = get_args()
    utils.load_settings(filepath=args.settings)
    db = utils.get_db()
    add_cbcs_label(db)
