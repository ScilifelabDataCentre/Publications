"Read a dump file. The database should be empty."

from __future__ import print_function

from publications import utils
from publications.scripts import dump


def get_args():
    parser = utils.get_command_line_parser(
        'Read a dump file into an empty database.')
    parser.add_argument('dumpfile', type=str, nargs=1,
                        help='Dump file, a gzipped tar file.')
    return parser.parse_args()

if __name__ == '__main__':
    args = get_args()
    utils.load_settings(filepath=args.settings)
    db = utils.get_db()
    dump.undump(db, args.dumpfile[0])
