# coding: utf-8
"Add NGI label for all NGI facilities."

from __future__ import print_function

import time

from publications import constants
from publications import settings
from publications import utils
from publications.publication import PublicationSaver

def get_args():
    parser = utils.get_command_line_parser(
        "Scrap all labels for NGI facilities and replace by it.")
    return parser.parse_args()

def add_ngi_label(db):
    "Add NGI label for all NGI facilities."
    qual_lookup = dict([(v,k) for k,v
                        in enumerate(settings['SITE_LABEL_QUALIFIERS'])])
    NGI = 'National Genomics Infrastructure (NGI)'
    OLD = [u'NGI Stockholm (Genomics Applications)',
           u'NGI Stockholm (Genomics Production)',
           u'NGI Uppsala (SNP&SEQ Technology Platform)',
           u'NGI Uppsala (Uppsala Genome Center)']
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
                           [max(qual_lookup[qual], qual_lookup[labels[NGI]])]
                except KeyError:
                    pass
                labels[NGI] = qual
                saver['labels'] = labels
                # No notes added, since old label will remain.

if __name__ == '__main__':
    args = get_args()
    utils.load_settings(filepath=args.settings)
    db = utils.get_db()
    add_ngi_label(db)
