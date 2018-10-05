#!/usr/bin/python2
"Web application server for a simple publications database."

from __future__ import print_function

import logging
import os

import tornado.web
import tornado.ioloop

from publications import settings
from publications import uimodules
from publications import utils

from publications.home import (Home,
                               Contact)
from publications.login import (Login,
                                Logout)
from publications.account import (Account,
                                  AccountJson,
                                  Accounts,
                                  AccountsJson,
                                  AccountAdd,
                                  AccountEdit,
                                  AccountReset,
                                  AccountPassword,
                                  AccountDisable,
                                  AccountEnable)
from publications.publication import (Publication,
                                      PublicationJson,
                                      Publications,
                                      PublicationsTable,
                                      PublicationsJson,
                                      PublicationsCsv,
                                      PublicationsUnverified,
                                      PublicationVerify,
                                      PublicationsNoPmid,
                                      PublicationsNoDoi,
                                      PublicationsModified,
                                      PublicationAdd,
                                      PublicationFetch,
                                      PublicationEdit,
                                      PublicationBlacklist,
                                      ApiPublicationFetch)
from publications.journal import (Journal,
                                  JournalJson,
                                  JournalEdit,
                                  Journals,
                                  JournalsJson)
from publications.label import (Label,
                                LabelJson,
                                LabelsList,
                                LabelsTable,
                                LabelsJson,
                                LabelAdd,
                                LabelEdit,
                                LabelMerge)
from publications.search import (Search,
                                 SearchJson)
from publications.logs import Logs


def get_args():
    parser = utils.get_command_line_parser(description=
        'Publications web server')
    parser.add_argument('-p', '--pidfile',
                        action='store', dest='pidfile', default=None,
                        metavar="FILE", help="filename of file containing PID")
    return parser.parse_args()

def main():
    args = get_args()
    utils.load_settings(filepath=args.settings)

    url = tornado.web.url
    handlers = [url(r'/', Home, name='home'),
                url(r'/site/([^/]+)', tornado.web.StaticFileHandler,
                    {'path': settings['SITE_DIR']}, name='site'),
                url(r'/publication/([^/.]+)', Publication, name='publication'),
                url(r'/publication/([^/.]+).json',
                    PublicationJson, name='publication_json'),
                url(r'/publications/(\d{4})',
                    Publications, name='publications_year'),
                url(r'/publications/(\d{4}).json',
                    PublicationsJson, name='publications_year_json'),
                url(r'/publications', Publications, name='publications'),
                url(r'/publications.json', 
                    PublicationsJson, name='publications_json'),
                url(r'/publications/csv', 
                    PublicationsCsv, name='publications_csv'),
                url(r'/publications/table/(\d{4})',
                    PublicationsTable, name='publications_table_year'),
                url(r'/publications/table',
                    PublicationsTable, name='publications_table'),
                url(r'/publications/unverified',
                    PublicationsUnverified, name='publications_unverified'),
                url(r'/verify/([^/]+)',
                    PublicationVerify, name='publication_verify'),
                url(r'/publications/no_pmid',
                    PublicationsNoPmid, name='publications_no_pmid'),
                url(r'/publications/no_doi',
                    PublicationsNoDoi, name='publications_no_doi'),
                url(r'/publications/modified',
                    PublicationsModified, name='publications_modified'),
                url(r'/edit/([^/]+)',
                    PublicationEdit, name='publication_edit'),
                url(r'/add',
                    PublicationAdd, name='publication_add'),
                url(r'/fetch',
                    PublicationFetch, name='publication_fetch'),
                url(r'/blacklist/([^/]+)',
                    PublicationBlacklist, name='publication_blacklist'),
                url(r'/journals', Journals, name='journals'),
                url(r'/journals.json', JournalsJson, name='journals_json'),
                url(r'/journal/([^/]+).json', JournalJson,name='journal_json'),
                url(r'/journal/([^/]+)', Journal, name='journal'),
                url(r'/journal/([^/]+)/edit', JournalEdit,name='journal_edit'),
                url(r'/labels', LabelsList, name='labels'),
                url(r'/labels.json', LabelsJson, name='labels_json'),
                url(r'/labels/table', LabelsTable, name='labels_table'),
                url(r'/label/([^/.]+).json', LabelJson, name='label_json'),
                url(r'/label/([^/.]+)', Label, name='label'),
                url(r'/label', LabelAdd, name='label_add'),
                url(r'/label/([^/]+)/edit', LabelEdit, name='label_edit'),
                url(r'/label/([^/]+)/merge', LabelMerge, name='label_merge'),
                url(r'/account/reset', AccountReset, name='account_reset'),
                url(r'/account/password',
                    AccountPassword, name='account_password'),
                url(r'/account/([^/]+).json', AccountJson,name='account_json'),
                url(r'/account/([^/]+)', Account, name='account'),
                url(r'/account/([^/]+)/edit',
                    AccountEdit, name='account_edit'),
                url(r'/account/([^/]+)/disable',
                    AccountDisable, name='account_disable'),
                url(r'/account/([^/]+)/enable',
                    AccountEnable, name='account_enable'),
                url(r'/accounts', Accounts, name='accounts'),
                url(r'/accounts.json', AccountsJson, name='accounts_json'),
                url(r'/account', AccountAdd, name='account_add'),
                url(r'/search', Search, name='search'),
                url(r'/search.json', SearchJson, name='search_json'),
                url(r'/logs/([^/]+)', Logs, name='logs'),
                url(r'/contact', Contact, name='contact'),
                url(r'/login', Login, name='login'),
                url(r'/logout', Logout, name='logout'),
                url(r'/api/publication',
                    ApiPublicationFetch, name='api_publication_fetch'),
                ]

    os.chdir(settings['ROOT'])
    application = tornado.web.Application(
        handlers=handlers,
        debug=settings.get('TORNADO_DEBUG', False),
        cookie_secret=settings['COOKIE_SECRET'],
        xsrf_cookies=True,
        ui_modules=uimodules,
        template_path='html',
        static_path='static',
        login_url=r'/login')
    application.listen(settings['PORT'], xheaders=True)
    pid = os.getpid()
    logging.info("web server PID %s at %s", pid, settings['BASE_URL'])
    if args.pidfile:
        with open(args.pidfile, 'w') as pf:
            pf.write(str(pid))
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    main()
