"""Search PubMed using specified criteria and fetch the references
setting them as unverified. Labels may be applied.
"""

from __future__ import print_function

import sys

import requests

from publications import constants
from publications import pubmed
from publications import utils
from publications.publication import PublicationSaver


def get_args():
    parser = utils.get_command_line_parser(
        description='Search PubMed and fetch references.')
    return parser.parse_args()

def search_pubmed(db, account, criteria):
    raise NotImplementedError


if __name__ == '__main__':
    (options, args) = get_args()
    utils.load_settings(filepath=options.settings)
