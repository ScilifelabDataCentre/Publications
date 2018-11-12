"CSV file of statistics for xrefs editing."

from __future__ import print_function

import csv
import json

from publications import constants
from publications import settings
from publications import utils


def xrefs_statistics(db, filename, since=None):
    "CSV file of statistics for xrefs editing."
    if since is None:
        since = utils.today()
    with open(filename, 'wb') as outfile:
        writer = csv.writer(outfile)
        write = writer.writerow
        write(('Site', settings['BASE_URL']))
        write(('Date', utils.today()))

        total = 0
        label_count = {}
        qualifier_count = {}
        has_xrefs = 0
        total_xrefs = 0
        xref_count = {}

        # Tot up added xrefs per curator.
        # Imperfect: wrongly added xrefs will be counted, even if deleted.
        # Get the original xrefs from the first log entry (first load).
        # For xref-changing log entries after the first:
        # curators[email][iuid] = set(all xrefs except those in orig)
        curators = {}

        for publication in utils.get_docs(db, 'publication/published'):
            print(publication['_id'])
            total += 1
            for label, qualifier in publication.get('labels', {}).items():
                try:
                    qualifiers = label_count[label]
                except KeyError:
                    qualifiers = label_count[label] = {}
                try:
                    qualifiers[qualifier] += 1
                except KeyError:
                    qualifiers[qualifier] = 1
            xrefs = publication.get('xrefs')
            if xrefs:
                has_xrefs += 1
                total_xrefs += len(xrefs)
                for xref in xrefs:
                    try:
                        xref_count[xref['db']] += 1
                    except KeyError:
                        xref_count[xref['db']] = 1
            logs = utils.get_docs(db,
                                  'log/doc',
                                  key=[publication['_id'], ''],
                                  last=[publication['_id'], constants.CEILING],
                                  descending=False)
            # Record any xrefs in first publication load.
            orig_xrefs = set(["%s:%s" % (x['db'], x['key'])
                              for x in
                              logs[0].get('changed', {}).get('xrefs', [])])
            # Get rid of irrelevant and too old changes.
            logs = [l for l in logs
                    if l['modified'] > since and 
                       l.get('changed', {}).get('xrefs')]
            if not logs: continue

            for log in logs:
                email = log['account']
                try:
                    account = curators[email]
                except KeyError:
                    account = curators[email] = {}
                xs = ["%s:%s" % (x['db'], x['key'])
                      for x in log['changed']['xrefs']]
                xs = [x for x in xs if x not in orig_xrefs]
                account.setdefault(publication['_id'], set()).update(xs)
        write(('Total publs', total))
        write(('Publs with xrefs', has_xrefs))
        write(('Total xrefs', total_xrefs))
        write(())
        write(['Labels', 'total'] + settings['SITE_LABEL_QUALIFIERS'])
        for label, count in sorted(label_count.items()):
            write([label, sum(label_count[label].values())] +
                  [count.get(q, 0) for q in settings['SITE_LABEL_QUALIFIERS']])
        write(())
        write(('Xrefs',))
        for db in sorted(xref_count):
            write((db, xref_count[db]))
        write(())
        write(('Xref curator', 'Total publs', 'Total xrefs'))
        for email in sorted(curators):
            publs = curators[email]
            total_publs = len(publs)
            new = set()
            for xrefs in publs.values():
                new.update(xrefs)
            total_xrefs = len(new)
            write((email, total_publs, total_xrefs))


if __name__ == '__main__':
    parser = utils.get_command_line_parser(
        'CSV file of statistics for xrefs editing.')
    parser.add_argument('-c', '--csvfile', metavar='FILE',
                        action='store', dest='csvfilename',
                        help='The name of the CSV file.')
    args = parser.parse_args()
    utils.load_settings(filepath=args.settings)
    db = utils.get_db()
    if args.csvfilename:
        csvfilename = args.csvfilename
    else:
        csvfilename = "statistics_{0}.csv".format(utils.today())
    xrefs_statistics(db, csvfilename)
