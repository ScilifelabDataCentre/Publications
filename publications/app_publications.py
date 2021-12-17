"Web application server for a publications database."

import logging
import os
import os.path
import sys

import tornado.web
import tornado.ioloop

from publications import constants
from publications import designs
from publications import settings
from publications import uimodules
from publications import utils

from publications.home import (Home,
                               Contact,
                               Settings,
                               Software,
                               Status,
                               Doc)
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
                                      PublicationsXlsx,
                                      PublicationsTxt,
                                      PublicationsNoPmid,
                                      PublicationsNoPmidJson,
                                      PublicationsNoDoi,
                                      PublicationsNoDoiJson,
                                      PublicationsNoLabel,
                                      PublicationsNoLabelJson,
                                      PublicationsDuplicates,
                                      PublicationsModified,
                                      PublicationAdd,
                                      PublicationFetch,
                                      PublicationEdit,
                                      PublicationResearchers,
                                      PublicationXrefs,
                                      PublicationBlacklist,
                                      PublicationsBlacklisted,
                                      PublicationUpdatePmid,
                                      PublicationFindPmid,
                                      PublicationUpdateDoi,
                                      ApiPublicationFetch,
                                      ApiPublicationLabels)
from publications.researcher import (Researcher,
                                     ResearcherJson,
                                     Researchers,
                                     ResearchersJson,
                                     ResearcherAdd,
                                     ResearcherEdit,
                                     ResearcherPublicationsCsv,
                                     ResearcherPublicationsXlsx,
                                     ResearcherPublicationsTxt,
                                     ResearcherPublicationsEdit)
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
from publications.subset import SubsetDisplay
from publications.logs import Logs


def get_application():
    url = tornado.web.url
    handlers = [url(r"/", Home, name="home"),
                url(r"/status", Status, name="status"),
                url(r"/docs/([^/]+)", Doc, name="doc"),
                url(r"/site/([^/]+)", tornado.web.StaticFileHandler,
                    {"path": settings["SITE_STATIC_DIR"]}, name="site"),
                url(r"/publication/([^/]{32,32})",
                    Publication, name="publication"),
                url(r"/publication/([^/]{32,32}).json",
                    PublicationJson, name="publication_json"),
                url(r"/publications/(\d{4})",
                    Publications, name="publications_year"),
                url(r"/publications/(\d{4}).json",
                    PublicationsJson, name="publications_year_json"),
                url(r"/publications", Publications, name="publications"),
                url(r"/publications.json", 
                    PublicationsJson, name="publications_json"),
                url(r"/publications/csv", 
                    PublicationsCsv, name="publications_csv"),
                url(r"/publications/xlsx", 
                    PublicationsXlsx, name="publications_xlsx"),
                url(r"/publications/txt", 
                    PublicationsTxt, name="publications_txt"),
                url(r"/publications/table/(\d{4})",
                    PublicationsTable, name="publications_table_year"),
                url(r"/publications/table",
                    PublicationsTable, name="publications_table"),
                url(r"/publications/no_pmid",
                    PublicationsNoPmid, name="publications_no_pmid"),
                url(r"/publications/no_pmid.json",
                    PublicationsNoPmidJson, name="publications_no_pmid_json"),
                url(r"/publications/no_doi",
                    PublicationsNoDoi, name="publications_no_doi"),
                url(r"/publications/no_doi.json",
                    PublicationsNoDoiJson, name="publications_no_doi_json"),
                url(r"/publications/no_label",
                    PublicationsNoLabel, name="publications_no_label"),
                url(r"/publications/no_label.json",
                    PublicationsNoLabelJson, name="publications_no_label_json"),
                url(r"/publications/duplicates",
                    PublicationsDuplicates, name="publications_duplicates"),
                url(r"/publications/modified",
                    PublicationsModified, name="publications_modified"),
                url(r"/edit/([^/]{32,32})",
                    PublicationEdit, name="publication_edit"),
                url(r"/researchers/([^/]{32,32})",
                    PublicationResearchers, name="publication_researchers"),
                url(r"/xrefs/([^/]{32,32})",
                    PublicationXrefs, name="publication_xrefs"),
                url(r"/add",
                    PublicationAdd, name="publication_add"),
                url(r"/fetch",
                    PublicationFetch, name="publication_fetch"),
                url(r"/blacklist/([^/]+)",
                    PublicationBlacklist, name="publication_blacklist"),
                url(r"/blacklisted",
                    PublicationsBlacklisted, name="publications_blacklisted"),
                url(r"/update/([^/]{32,32})/pmid",
                    PublicationUpdatePmid, name="publication_update_pmid"),
                url(r"/update/([^/]{32,32})/find_pmid",
                    PublicationFindPmid, name="publication_find_pmid"),
                url(r"/update/([^/]{32,32})/doi",
                    PublicationUpdateDoi, name="publication_update_doi"),
                url(r"/researcher", ResearcherAdd, name="researcher_add"),
                url(r"/researchers_json",
                    ResearchersJson, name="researchers_json"),
                url(r"/researchers", Researchers, name="researchers"),
                url(r"/researcher/([^/]+).json",
                    ResearcherJson, name="researcher_json"),
                url(r"/researcher/([^/]+)", Researcher, name="researcher"),
                url(r"/researcher/([^/]+)/edit",
                    ResearcherEdit, name="researcher_edit"),
                url(r"/researcher/([^/]+)/publications.csv",
                    ResearcherPublicationsCsv,
                    name="researcher_publications_csv"),
                url(r"/researcher/([^/]+)/publications.xlsx",
                    ResearcherPublicationsXlsx,
                    name="researcher_publications_xlsx"),
                url(r"/researcher/([^/]+)/publications.txt",
                    ResearcherPublicationsTxt,
                    name="researcher_publications_txt"),
                url(r"/researcher/([^/]+)/publications/edit", 
                    ResearcherPublicationsEdit,
                    name="researcher_publications_edit"),
                url(r"/journals", Journals, name="journals"),
                url(r"/journals.json", JournalsJson, name="journals_json"),
                url(r"/journal/([^/]+).json", JournalJson,name="journal_json"),
                url(r"/journal/([^/]+)", Journal, name="journal"),
                url(r"/journal/([^/]+)/edit", JournalEdit,name="journal_edit"),
                url(r"/labels", LabelsList, name="labels"),
                url(r"/labels.json", LabelsJson, name="labels_json"),
                url(r"/labels/table", LabelsTable, name="labels_table"),
                # These two label path patterns need to be checked first.
                url(r"/label/([^\.]+)/edit", LabelEdit, name="label_edit"),
                url(r"/label/([^\.]+)/merge", LabelMerge, name="label_merge"),
                url(r"/label/([^\.]+).json", LabelJson, name="label_json"),
                url(r"/label/([^\.]+)", Label, name="label"),
                url(r"/label", LabelAdd, name="label_add"),
                url(r"/account/reset", AccountReset, name="account_reset"),
                url(r"/account/password",
                    AccountPassword, name="account_password"),
                url(r"/account/([^/]+).json", AccountJson,name="account_json"),
                url(r"/account/([^/]+)", Account, name="account"),
                url(r"/account/([^/]+)/edit",
                    AccountEdit, name="account_edit"),
                url(r"/account/([^/]+)/disable",
                    AccountDisable, name="account_disable"),
                url(r"/account/([^/]+)/enable",
                    AccountEnable, name="account_enable"),
                url(r"/accounts", Accounts, name="accounts"),
                url(r"/accounts.json", AccountsJson, name="accounts_json"),
                url(r"/account", AccountAdd, name="account_add"),
                url(r"/search", Search, name="search"),
                url(r"/search.json", SearchJson, name="search_json"),
                url(r"/subset", SubsetDisplay, name="subset"),
                url(r"/logs/([^/]+)", Logs, name="logs"),
                url(r"/contact", Contact, name="contact"),
                url(r"/settings", Settings, name="settings"),
                url(r"/software", Software, name="software"),
                url(r"/login", Login, name="login"),
                url(r"/logout", Logout, name="logout"),
                url(r"/api/publication",
                    ApiPublicationFetch, name="api_publication_fetch"),
                url(r"/api/publication/([^/]{32,32})/labels",
                    ApiPublicationLabels, name="api_publication_labels"),
                ]

    return tornado.web.Application(
        handlers=handlers,
        debug=settings.get("TORNADO_DEBUG", False),
        cookie_secret=settings["COOKIE_SECRET"],
        xsrf_cookies=True,
        ui_modules=uimodules,
        template_path=os.path.join(constants.ROOT, "templates"),
        static_path=os.path.join(constants.ROOT, "static"),
        login_url=r"/login")

def main():
    if len(sys.argv) == 2:
        filepath = sys.argv[1]
    else:
        filepath = None
    utils.load_settings(filepath=filepath)
    designs.load_design_documents(utils.get_db())
    application = get_application()
    application.listen(settings["PORT"], xheaders=True)
    pid = os.getpid()
    if settings["PIDFILE"]:
        with open(settings["PIDFILE"], "w") as pf:
            pf.write(str(pid))
    logging.info(f"web server PID {pid} at {settings['BASE_URL']}")
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
