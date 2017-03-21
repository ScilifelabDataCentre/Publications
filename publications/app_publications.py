#!/usr/bin/env python2
"Web application server for a simple publications database."

from __future__ import print_function

import logging
import os

import tornado.web
import tornado.ioloop

from publications import settings
from publications import uimodules
from publications import utils
from publications.requesthandler import RequestHandler

from publications.home import Home
from publications.login import Login, Logout
from publications.account import Account
from publications.publication import (Publication,
                                      PublicationFetch,
                                      PublicationEdit,
                                      PublicationTrash)
from publications.search import Search
from publications.logs import Logs


class Dummy(RequestHandler):
    def get(self, *args, **kwargs):
        raise NotImplementedError


def get_args():
    parser = utils.get_command_line_parser(description=
        'Publications web server')
    parser.add_option('-p', '--pidfile',
                      action='store', dest='pidfile', default=None,
                      metavar="FILE", help="filename of file containing PID")
    return parser.parse_args()

def main():
    (options, args) = get_args()
    utils.load_settings(filepath=options.settings)

    url = tornado.web.url
    handlers = [url(r'/', Home, name='home'),
                url(r'/site/([^/]+)', tornado.web.StaticFileHandler,
                    {'path': settings['SITE_DIR']}, name='site'),
                url(r'/publ/([^/]+)', Publication, name='publication'),
                url(r'/edit/([^/]+)',
                    PublicationEdit, name='publication_edit'),
                url(r'/fetch',
                    PublicationFetch, name='publication_fetch'),
                url(r'/trash/([^/]+)',
                    PublicationTrash, name='publication_trash'),
                url(r'/login', Login, name='login'),
                url(r'/logout', Logout, name='logout'),
                url(r'/account/([^/]+)', Dummy, name='account'),
                url(r'/search', Search, name='search'),
                url(r'/logs/([^/]+)', Logs, name='logs'),
                ]

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
    if options.pidfile:
        with open(options.pidfile, 'w') as pf:
            pf.write(str(pid))
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    main()
