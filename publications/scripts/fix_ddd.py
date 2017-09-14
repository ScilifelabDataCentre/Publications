# coding: utf-8
"Add DDD label for all DDD facilities."

from __future__ import print_function

import time

from publications import constants
from publications import settings
from publications import utils
from publications.publication import PublicationSaver

def get_args():
    parser = utils.get_command_line_parser(
        "Scrap all labels for DDD facilities and replace by it.")
    return parser.parse_args()

def add_ddd_label(db):
    "Add DDD label for all DDD facilities."
    qual_lookup = dict([(v,k) for k,v
                        in enumerate(settings['SITE_LABEL_QUALIFIERS'])])
    DDD = 'Drug Discovery and Development (DDD)'
    OLD = [u'ADME of Therapeutics (UDOPP)',
           u'Biochemical and Cellular Screening',
           u'Biophysical Screening and Characterization',
           u'Human Antibody Therapeutics',
           u'Medicinal Chemistry – Hit2Lead',
           u'In Vitro and Systems Pharmacology',
           u'Medicinal Chemistry – Lead Identification',
           u'Protein Expression and Characterization']
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
                           [max(qual_lookup[qual], qual_lookup[labels[DDD]])]
                except KeyError:
                    pass
                labels[DDD] = qual
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
    add_ddd_label(db)
