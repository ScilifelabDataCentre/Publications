"Publication pages."

from __future__ import print_function

from collections import OrderedDict as OD
import csv
from cStringIO import StringIO

import requests
import tornado.web

from . import constants
from . import crossref
from . import pubmed
from . import settings
from . import utils
from .saver import Saver, SaverError
from .requesthandler import RequestHandler, ApiMixin


class PublicationSaver(Saver):
    doctype = constants.PUBLICATION

    def check_published(self, value):
        utils.to_date(value)

    def convert_published(self, value):
        return utils.to_date(value)

    def check_epublished(self, value):
        utils.to_date(value)

    def convert_epublished(self, value):
        if value:
            return utils.to_date(value)
        else:
            return None

    def set_title(self):
        "Set title from form data."
        assert self.rqh, 'requires http request context'
        self['title'] = self.rqh.get_argument('title', '') or '[no title]'

    def set_authors(self):
        "Set authors list from form data."
        assert self.rqh, 'requires http request context'
        authors = []
        for author in self.rqh.get_argument('authors', '').split('\n'):
            author = author.strip()
            if not author: continue
            try:
                family, given = author.split(',', 1)
            except ValueError:  # Name written as 'Per Kraulis'
                parts = author.split()
                family = parts[-1]
                given = ' '.join(parts[:-1])
            else:               # Name written as 'Kraulis, Per'
                family = family.strip()
                if not family:
                    family = author
                    given = ''
                given = given.strip()
            initials = ''.join([c[0] for c in given.split()])
            authors.append(
                dict(family=family,
                     family_normalized=utils.to_ascii(family).lower(),
                     given=given,
                     given_normalized=utils.to_ascii(given).lower(),
                     initials=initials,
                     initials_normalized=utils.to_ascii(initials).lower()))
        self['authors'] = authors

    def set_pmid_doi(self):
        "Set pmid and doi from form data. No validity checks are made."
        assert self.rqh, 'requires http request context'
        self['pmid'] = self.rqh.get_argument('pmid', '') or None
        self['doi'] = self.rqh.get_argument('doi', '') or None

    def set_published(self):
        "Set published and epublished from form data."
        assert self.rqh, 'requires http request context'
        self['published'] = self.rqh.get_argument('published', '') or None
        self['epublished'] = self.rqh.get_argument('epublished','') or None

    def set_journal(self):
        "Set journal from form data."
        assert self.rqh, 'requires http request context'
        journal = dict(title=self.rqh.get_argument('journal', '') or None)
        for key in ['issn', 'volume', 'issue', 'pages']:
            journal[key] = self.rqh.get_argument(key, '') or None
        self['journal'] = journal

    def set_abstract(self):
        "Set abstract from form data."
        assert self.rqh, 'requires http request context'
        self['abstract'] = self.rqh.get_argument('abstract', '') or None

    def fix_journal(self):
        """Set the appropriate journal title and ISSN if not done.
        Creates the journal entity if it does not exist."""
        assert self.rqh, 'requires http request context'
        doc = None
        journal = self['journal'].copy()
        issn = journal.get('issn')
        title = journal.get('title')
        if issn:
            try:
                doc = self.rqh.get_doc(issn, 'journal/issn')
            except KeyError:
                if title:
                    try:
                        doc = self.rqh.get_doc(title, 'journal/title')
                    except KeyError:
                        doc = None
                    else:
                        if issn != doc['issn']:
                            journal['issn'] = doc['issn']
            else:
                if title != doc['title']:
                    journal['title'] = doc['title']
        self['journal'] = journal
        # Create journal entity if it does not exist, and if sufficient data.
        if doc is None and issn and title:
            # Import done here to avoid circularity.
            from publications.journal import JournalSaver
            with JournalSaver(db=self.db) as saver:
                saver['issn'] = issn
                saver['title'] = title


class PublicationMixin(object):
    "Mixin for access check methods."

    def is_editable(self, publication):
        """Is the publication editable by the current user?
        Implies acquireable."""
        if not self.is_curator(): return False
        try:
            acquired = publication['acquired']
        except KeyError:
            return True
        else:
            if acquired['account'] == self.current_user['email']: return True
        return False

    def check_editable(self, publication):
        """Check that the publication is editable by the current user.
        Implies acquireable."""
        if self.is_editable(publication): return
        raise ValueError('You many not edit the publication.')

    def is_releasable(self, publication):
        "Is the publication releasable by the current user?"
        if not self.is_curator(): return False
        try:
            acquired = publication['acquired']
        except KeyError:
            return False
        if self.is_admin(): return True
        if acquired['account'] == self.current_user['email']: return True
        if acquired['deadline'] < utils.timestamp(): return True
        return False

    def check_releasable(self, publication):
        "Check that the publication can be released by the current user."
        if self.is_releasable(publication): return
        raise ValueError('You cannot release the publication.')

    def is_deletable(self, publication):
        "Is the publication deletable by the current user?"
        if not self.is_curator(): return False
        try:
            acquired = publication['acquired']
        except KeyError:
            return True
        else:
            if acquired['account'] == self.current_user['email']: return True
        return False

    def check_deletable(self, publication):
        "Check that the publication is deletable by the current user."
        if self.is_deletable(publication): return
        raise ValueError('You may not delete the publication.')

    def get_form_labels(self, publication=None):
        "Get labels from form input and allowed for the account."
        allowed_labels = self.get_allowed_labels()
        if publication:
            labels = publication.get('labels', {}).copy()
        else:
            labels = {}
        use_labels = set(self.get_arguments('label'))
        for label in allowed_labels:
            if label in use_labels:
                labels[label] = self.get_argument("%s_qualifier" % label, None)
            else:
                labels.pop(label, None)
        return labels

    def get_allowed_labels(self):
        "Get the set of allowed labels for the account."
        if self.is_admin():
            return set([l['value'] for l in self.get_docs('label/value')])
        else:
            return set(self.current_user['labels'])

    def fetch(self, identifier, override=False, verify=False, labels={}):
        """Fetch the publication given by identifier (PMID or DOI).
        override: If True, overrides the blacklist.
        verify: Set the verified flag of a new publication.
        labels: Dictionary of labels (key: label, value: qualifier) to set.
        Raise IOError if no such publication found, or other error.
        Raise KeyError if publication is in the blacklist (and not override).
        """
        # If identifier in blacklist registry, skip unless override
        blacklisted = self.get_blacklisted(identifier)
        if blacklisted:
            if override:
                self.db.delete(blacklisted)
            else:
                raise KeyError(identifier)
        # Has it already been fetched?
        try:
            old = self.get_publication(identifier, unverified=True)
        except KeyError:
            old = None
        # Fetch from external source according to identifier type.
        if constants.PMID_RX.match(identifier):
            try:
                new = pubmed.fetch(identifier)
            except (IOError, ValueError, requests.exceptions.Timeout), msg:
                raise IOError("%s: %s" % (identifier, str(msg)))
            else:
                if old is None:
                    # Maybe the publication has been loaded by DOI?
                    try:
                        old = self.get_publication(new.get('doi'))
                    except KeyError:
                        pass
        # Not PMID, must be DOI
        else:
            try:
                new = crossref.fetch(identifier)
            except (IOError, requests.exceptions.Timeout), msg:
                raise IOError("%s: %s" % (identifier, str(msg)))
            else:
                if old is None:
                    # Maybe the publication has been loaded by PMID?
                    try:
                        old = self.get_publication(new.get('pmid'))
                    except KeyError:
                        pass
        # Check blacklist registry again; other external id may be there.
        blacklisted = self.get_blacklisted(new.get('pmid'))
        if blacklisted:
            if override:
                self.db.delete(blacklisted)
            else:
                raise KeyError(identifier)
        blacklisted = self.get_blacklisted(new.get('doi'))
        if blacklisted:
            if override:
                self.db.delete(blacklisted)
            else:
                raise KeyError(identifier)
        allowed_labels = self.get_allowed_labels()
        for label, qualifier in labels.items():
            if label not in allowed_labels:
                labels.pop(label)
            elif qualifier not in settings['SITE_LABEL_QUALIFIERS']:
                labels[label] = None
        # Update the existing entry.
        if old:
            updated_labels = old['labels'].copy()
            updated_labels.update(labels)
            with PublicationSaver(old, rqh=self) as saver:
                for key in new:
                    saver[key] = new[key]
                saver.fix_journal()
                saver['labels'] = updated_labels
                if verify:      # Do not swap back to unverified.
                    saver['verified'] = True
            return old
        # Else create a new entry.
        else:
            with PublicationSaver(new, rqh=self) as saver:
                saver.fix_journal()
                saver['labels'] = labels
                saver['verified'] = verify
            return new


class Publication(PublicationMixin, RequestHandler):
    "Display the publication."

    def get(self, identifier):
        "Display the publication."
        try:
            publication = self.get_publication(identifier)
        except KeyError, msg:
            self.see_other('home', error=str(msg))
            return
        self.render('publication.html',
                    publication=publication,
                    is_editable=self.is_editable(publication),
                    is_releasable=self.is_releasable(publication),
                    is_deletable=self.is_deletable(publication))

    @tornado.web.authenticated
    def post(self, identifier):
        if self.get_argument('_http_method', None) == 'delete':
            self.delete(identifier)
            return
        raise tornado.web.HTTPError(405, reason='POST only allowed for DELETE')

    @tornado.web.authenticated
    def delete(self, identifier):
        try:
            publication = self.get_publication(identifier)
            self.check_deletable(publication)
        except (KeyError, ValueError), msg:
            self.see_other('home', error=str(msg))
            return
        # Delete log entries
        for log in self.get_logs(publication['_id']):
            self.db.delete(log)
        self.db.delete(publication)
        self.see_other('home')


class PublicationJson(Publication):
    "Publication JSON data."

    def render(self, template, **kwargs):
        self.write(self.get_publication_json(kwargs['publication']))


class Publications(RequestHandler):
    "Publications list page."

    TEMPLATE = 'publications.html'

    def get(self, year=None):
        if year:
            publications = self.get_docs('publication/year', key=year)
            publications.sort(key=lambda i: i['published'], reverse=True)
        else:
            publications = self.get_docs('publication/published',
                                         key=constants.CEILING,
                                         last='',
                                         descending=True)
        self.render(self.TEMPLATE, publications=publications, year=year)


class PublicationsTable(Publications):
    "Publications table page."

    TEMPLATE = 'publications_table.html'


class PublicationsJson(Publications):
    "Publications JSON output."

    def render(self, template, **kwargs):
        URL = self.absolute_reverse_url
        publications = kwargs['publications']
        result = OD()
        result['entity'] = 'publications'
        result['timestamp'] = utils.timestamp()
        year = kwargs['year']
        if year:
            result['year'] = year
        result['links'] = links = OD()
        if year:
            links['self'] = {'href': URL('publications_year_json', year)}
            links['display'] = {'href': URL('publications_year', year)}
        else:
            links['self'] = {'href': URL('publications_json')}
            links['display'] = {'href': URL('publications')}
        result['publications_count'] = len(publications)
        result['publications'] = [self.get_publication_json(publication)
                                  for publication in publications]
        self.write(result)


class PublicationsCsv(Publications):
    "Publications CSV output."

    def get(self):
        "Show output selection page."
        self.render('publications_csv.html',
                    year=self.get_argument('year', None),
                    labels=set(self.get_arguments('label')),
                    all_labels=sorted([l['value']
                                       for l in self.get_docs('label/value')]))

    # authentication is *not* required!
    def post(self):
        "Produce CSV output."
        publications = []
        years = self.get_arguments('years')
        all_authors = utils.to_bool(self.get_argument('all_authors', 'false'))
        issn = utils.to_bool(self.get_argument('issn', 'false'))
        labels = set(self.get_arguments('labels'))
        single_label = utils.to_bool(self.get_argument('single_label','false'))
        delimiter = self.get_argument('delimiter', '').lower()
        if delimiter == 'comma':
            delimiter = ','
        elif delimiter == 'semi-colon':
            delimiter = ';'
        else:
            delimiter = ','
        encoding = self.get_argument('encoding', '').lower()
        if encoding not in ('utf-8', 'iso-8859-1'):
            encoding = 'utf-8'
        if years:
            for year in years:
                publications.extend(self.get_docs('publication/year',key=year))
        else:
            publications = self.get_docs('publication/published',
                                         key=constants.CEILING,
                                         last='',
                                         descending=True)
        if labels:
            kept = []
            for publication in publications:
                for label in publication.get('labels', {}):
                    if label in labels:
                        kept.append(publication)
                        break
            publications = kept
        publications.sort(key=lambda p: p.get('published'), reverse=True)
        csvbuffer = StringIO()
        writer = csv.writer(csvbuffer, delimiter=delimiter)
        row = ['Title',
               'Authors',
               'Journal']
        if issn:
            row.append('ISSN')
        row.extend(
            ['Year', 
             'Published',
             'E-published',
             'Volume',
             'Issue',
             'Pages',
             'DOI',
             'PMID',
             'Labels',        # pos = 11 or 12
             'Qualifiers',    # pos = 12 or 13
             'IUID',
             'URL',
             'DOI URL',
             'PubMed URL',
            ])
        writer.writerow(row)
        if issn:
            offset = 1
        else:
            offset = 0
        for publication in publications:
            year = publication.get('published')
            if year:
                year = year.split('-')[0]
            journal = publication.get('journal') or {}
            pubmed_url = publication.get('pmid')
            if pubmed_url:
                pubmed_url = constants.PUBMED_URL % pubmed_url
            doi_url = publication.get('doi')
            if doi_url:
                doi_url = constants.DOI_URL % doi_url
            lookup = publication.get('labels', {})
            labels = sorted(lookup.keys())
            qualifiers = [lookup[k] or '' for k in labels]
            row = [
                publication.get('title'),
                utils.get_formatted_authors(publication['authors'],
                                            complete=all_authors),
                journal.get('title')]
            if issn:
                row.append(journal.get('issn'))
            row.extend(
                [year,
                 publication.get('published'),
                 publication.get('epublished'),
                 journal.get('volume'),
                 journal.get('issue'),
                 journal.get('pages'),
                 publication.get('doi'),
                 publication.get('pmid'),
                 '',             # pos = 11 or 12
                 '',             # pos = 12 or 13
                 publication['_id'],
                 self.absolute_reverse_url('publication', publication['_id']),
                 doi_url,
                 pubmed_url,
                ]
            )
            row = [(i or '').encode(encoding, errors='replace') for i in row]
            if single_label:
                for label, qualifier in zip(labels, qualifiers):
                    row[11+offset] = label.encode(encoding, errors='replace')
                    row[12+offset] = qualifier.encode(encoding, errors='replace')
                    utils.write_safe_csv_row(writer, row)
            else:
                row[11+offset] = ', '.join(labels).encode(encoding, errors='replace')
                row[12+offset] = ', '.join([q for q in qualifiers if q])
                utils.write_safe_csv_row(writer, row)
        self.write(csvbuffer.getvalue())
        self.set_header('Content-Type', constants.CSV_MIME)
        self.set_header('Content-Disposition', 
                        'attachment; filename="publications.csv')


class PublicationsUnverified(RequestHandler):
    """Unverified publications page.
    List according to which labels the account may use.
    """

    @tornado.web.authenticated
    def get(self):
        if self.is_admin():
            publications = self.get_docs('publication/unverified',
                                         descending=True)
        else:
            lookup = {}
            for label in self.current_user.get('labels'):
                docs = self.get_docs('publication/label_unverified',
                                     key=label.lower())
                for doc in docs:
                    lookup[doc['_id']] = doc
            publications = lookup.values()
            publications.sort(key=lambda i: i['published'], reverse=True)
        self.render('publications_unverified.html', publications=publications)


class PublicationsNoPmid(RequestHandler):
    "Publications lacking PMID."

    def get(self):
        publications = self.get_docs('publication/no_pmid',
                                     descending=True)
        self.render('publications_no_pmid.html', publications=publications)


class PublicationsNoDoi(RequestHandler):
    "Publications lacking DOI."

    def get(self):
        publications = self.get_docs('publication/no_doi',
                                     descending=True)
        self.render('publications_no_doi.html', publications=publications)


class PublicationsModified(PublicationMixin, RequestHandler):
    "List of most recently modified publications."

    def get(self):
        self.check_curator()
        docs = self.get_docs('publication/modified',
                             descending=True,
                             limit=settings['LONG_PUBLICATIONS_LIST_LIMIT'])
        self.render('publications_modified.html', publications=docs)


class PublicationAdd(PublicationMixin, RequestHandler):
    "Add a publication by hand."

    @tornado.web.authenticated
    def get(self):
        self.check_curator()
        self.render('publication_add.html', labels=self.get_allowed_labels())

    @tornado.web.authenticated
    def post(self):
        self.check_curator()
        with PublicationSaver(rqh=self) as saver:
            saver.set_title()
            saver.set_authors()
            saver.set_published()
            saver.set_journal()
            saver.set_abstract()
            saver['labels'] = self.get_form_labels()
            # Publication should not be verified automatically by add!
            # It must be possible for admin to change labels in order to
            # challenge the relevant curators to verify or blacklist.
            publication = saver.doc
        self.see_other('publication', publication['_id'])


class PublicationFetch(PublicationMixin, RequestHandler):
    "Fetch publication(s) given list of DOIs or PMIDs."

    @tornado.web.authenticated
    def get(self):
        self.check_curator()
        docs = self.get_docs('publication/modified',
                             key=constants.CEILING,
                             last=utils.today(-1),
                             descending=True,
                             limit=settings['PUBLICATIONS_FETCHED_LIMIT'])
        self.render('publication_fetch.html', 
                    labels=self.get_allowed_labels(),
                    publications=docs)

    @tornado.web.authenticated
    def post(self):
        self.check_curator()
        identifiers = self.get_argument('identifiers', '').split()
        identifiers = [utils.strip_prefix(i) for i in identifiers]
        identifiers = [i for i in identifiers if i]
        override = utils.to_bool(self.get_argument('override', False))
        verify = utils.to_bool(self.get_argument('verify', False))
        count = 0
        errors = []
        messages = []
        for identifier in identifiers:
            # Skip if number of loaded publications reached the limit
            if count >= settings['PUBLICATIONS_FETCHED_LIMIT']: break

            # try:
            #     self.fetch(identifier, override, verify)
            # except KeyError as message:
            #     messages.append(str(message))
            # except IOError as error:
            #     errors.append(str(error))

            # If identifier in blacklist registry, skip unless override
            blacklisted = self.get_blacklisted(identifier)
            if blacklisted:
                if override:
                    self.db.delete(blacklisted)
                else:
                    messages.append(identifier)
                    continue
            # Has it already been fetched?
            try:
                old = self.get_publication(identifier, unverified=True)
            except KeyError:
                old = None
            # Fetch from external source according to identifier type.
            if constants.PMID_RX.match(identifier):
                try:
                    new = pubmed.fetch(identifier)
                except (IOError, ValueError, requests.exceptions.Timeout), msg:
                    errors.append("%s: %s" % (identifier, str(msg)))
                    continue
                else:
                    if old is None:
                        # Maybe the publication has been loaded by DOI?
                        try:
                            old = self.get_publication(new.get('doi'))
                        except KeyError:
                            pass
            # Not PMID, must be DOI
            else:
                try:
                    new = crossref.fetch(identifier)
                except (IOError, requests.exceptions.Timeout), msg:
                    errors.append("%s: %s" % (identifier, str(msg)))
                    continue
                else:
                    if old is None:
                        # Maybe the publication has been loaded by PMID?
                        try:
                            old = self.get_publication(new.get('pmid'))
                        except KeyError:
                            pass
            # Update count of number of fetched publications.
            count += 1
            # Check blacklist registry again; other external id may be there.
            blacklisted = self.get_blacklisted(new.get('pmid'))
            if blacklisted:
                if override:
                    self.db.delete(blacklisted)
                else:
                    messages.append(identifier)
                    continue
            blacklisted = self.get_blacklisted(new.get('doi'))
            if blacklisted:
                if override:
                    self.db.delete(blacklisted)
                else:
                    messages.append(identifier)
                    continue
            # Update the existing entry.
            if old:
                with PublicationSaver(old, rqh=self) as saver:
                    for key in new:
                        saver[key] = new[key]
                    saver['labels'] = self.get_form_labels(old)
                    saver.fix_journal()
            # Else create a new entry.
            else:
                with PublicationSaver(new, rqh=self) as saver:
                    saver.fix_journal()
                    saver['labels'] = self.get_form_labels(new)
                    saver['verified'] = verify
        kwargs = {}
        if errors:
            kwargs['error'] = constants.FETCH_ERROR + ', '.join(errors)
        if messages:
            kwargs['message'] = constants.BLACKLISTED_MESSAGE + \
                                ', '.join(messages)
        self.see_other('publication_fetch', **kwargs)


class PublicationEdit(PublicationMixin, RequestHandler):
    "Edit the publication."

    @tornado.web.authenticated
    def get(self, iuid):
        try:
            publication = self.get_publication(iuid)
            self.check_editable(publication)
        except (KeyError, ValueError), msg:
            self.see_other('home', error=str(msg))
            return
        self.render('publication_edit.html',
                    publication=publication,
                    labels=self.get_allowed_labels())

    @tornado.web.authenticated
    def post(self, iuid):
        try:
            publication = self.get_publication(iuid)
            self.check_editable(publication)
        except (KeyError, ValueError), msg:
            self.see_other('home', error=str(msg))
            return
        try:
            with PublicationSaver(doc=publication, rqh=self) as saver:
                saver.check_revision()
                saver.set_title()
                saver.set_authors()
                saver.set_pmid_doi()
                saver.set_published()
                saver.set_journal()
                saver.set_abstract()
                saver['labels'] = self.get_form_labels(publication)
                saver['notes'] = self.get_argument('notes', None)
                # Publication should not be verified automatically by edit!
                # It must be possible for admin to change labels in order to
                # challenge the relevant curators to verify or blacklist.
        except SaverError, msg:
            self.set_error_flash(utils.REV_ERROR)
        self.see_other('publication', publication['_id'])


class PublicationVerify(PublicationMixin, RequestHandler):
    "Verify publication."

    @tornado.web.authenticated
    def post(self, identifier):
        self.check_curator()
        try:
            publication = self.get_publication(identifier)
        except KeyError, msg:
            self.see_other('home', error=str(msg))
            return
        with PublicationSaver(publication, rqh=self) as saver:
            saver['verified'] = True
        try:
            self.redirect(self.get_argument('next'))
        except tornado.web.MissingArgumentError:
            self.see_other('publication', publication['_id'])


class PublicationBlacklist(PublicationMixin, RequestHandler):
    "Blacklist a publication and record its external identifiers."

    @tornado.web.authenticated
    def post(self, identifier):
        try:
            publication = self.get_publication(identifier)
            self.check_deletable(publication)
        except (KeyError, ValueError), msg:
            self.see_other('home', error=str(msg))
            return
        blacklist = {constants.DOCTYPE: constants.BLACKLIST,
                 'title': publication['title'],
                 'pmid': publication.get('pmid'),
                 'doi': publication.get('doi'),
                 'created': utils.timestamp(),
                 'owner': self.current_user['email']}
        self.db[utils.get_iuid()] = blacklist
        self.delete_entity(publication)
        try:
            self.redirect(self.get_argument('next'))
        except tornado.web.MissingArgumentError:
            self.see_other('home')


class PublicationAcquire(PublicationMixin, RequestHandler):
    "The current user acquires the publication for exclusive editing."

    @tornado.web.authenticated
    def post(self, identifier):
        try:
            publication = self.get_publication(identifier)
            self.check_editable(publication)
        except (KeyError, ValueError), msg:
            self.see_other('home', error=str(msg))
            return
        with PublicationSaver(publication, rqh=self) as saver:
            deadline = utils.timestamp(days=settings['PUBLICATION_ACQUIRE_PERIOD'])
            saver['acquired'] = {'account': self.current_user['email'],
                                 'deadline': deadline}
        self.see_other('publication', publication['_id'])


class PublicationRelease(PublicationMixin, RequestHandler):
    "The publication is released from exclusive editing."

    @tornado.web.authenticated
    def post(self, identifier):
        try:
            publication = self.get_publication(identifier)
            self.check_releasable(publication)
        except (KeyError, ValueError), msg:
            self.see_other('home', error=str(msg))
            return
        with PublicationSaver(publication, rqh=self) as saver:
            del saver['acquired']
        self.see_other('publication', publication['_id'])


class ApiPublicationFetch(PublicationMixin, ApiMixin, RequestHandler):
    "Fetch a publication given its PMID or DOI."

    @tornado.web.authenticated
    def post(self):
        self.check_curator()
        data = self.get_json_body()
        try:
            identifier = data['identifier']
        except KeyError:
            raise tornado.web.HTTPError(400, reason='no identifier given')
        override = bool(data.get('override'))
        verify = bool(data.get('verify'))
        labels = data.get('labels', {})
        try:
            doc = self.fetch(identifier, override, verify, labels)
        except IOError as msg:
            raise tornado.web.HTTPError(400, reason=str(msg))
        except KeyError as msg:
            raise tornado.web.HTTPError(409, reason=str(msg))
        self.write(
            dict(iuid=doc['_id'],
                 href=self.absolute_reverse_url('publication', doc['_id'])))
