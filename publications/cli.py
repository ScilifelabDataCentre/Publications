"Command line interface to the Publications database."

import csv
import functools
import json
import os
import time
import sys

import click
import couchdb2

from publications import constants
from publications import crossref
from publications import pubmed
from publications import settings
from publications import utils
from publications.account import AccountSaver
from publications.publication import PublicationSaver, fetch_publication
from publications.subset import Subset, get_parser
import publications.app_publications
import publications.writer


@click.group()
@click.option("-s", "--settings", help="Path of settings YAML file.")
@click.option("--log", flag_value=True, default=False, help="Enable logging output.")
def cli(settings, log):
    utils.load_settings(settings, log=log)


@cli.command()
def destroy_database():
    "Hard delete of the entire database, including the instance within CouchDB."
    server = utils.get_dbserver()
    try:
        db = server[settings["DATABASE_NAME"]]
    except couchdb2.NotFoundError as error:
        raise click.ClickException(str(error))
    db.destroy()
    click.echo(f"""Destroyed database '{settings["DATABASE_NAME"]}'.""")


@cli.command()
def create_database():
    "Create the database instance within CouchDB. Load the design document."
    server = utils.get_dbserver()
    if settings["DATABASE_NAME"] in server:
        raise click.ClickException(
            f"""Database '{settings["DATABASE_NAME"]}' already exists."""
        )
    server.create(settings["DATABASE_NAME"])
    click.echo(f"""Created database '{settings["DATABASE_NAME"]}'.""")
    utils.load_design_documents()


@cli.command()
def initialize():
    """Initialize database; load design documents.
    No longer needed. Kept just for backwards compatibility.
    """
    utils.load_design_documents()


@cli.command()
def counts():
    "Output counts of some database entities."
    db = utils.load_design_documents()
    click.echo(f"{utils.get_count(db, 'publication', 'year'):>5} publications")
    click.echo(f"{utils.get_count(db, 'label', 'value'):>5} labels")
    click.echo(f"{utils.get_count(db, 'account', 'email'):>5} accounts")
    click.echo(f"{utils.get_count(db, 'researcher', 'name'):>5} researchers")


@cli.command()
@click.option(
    "-d",
    "--dumpfile",
    type=str,
    help="The path of the Publications database dump file.",
)
@click.option(
    "-D",
    "--dumpdir",
    type=str,
    help="The directory to write the dump file in, using the standard name.",
)
@click.option(
    "--progressbar/--no-progressbar", default=True, help="Display a progressbar."
)
def dump(dumpfile, dumpdir, progressbar):
    "Dump all data in the database to a .tar.gz dump file."
    db = utils.get_db()
    if not dumpfile:
        dumpfile = "dump_{0}.tar.gz".format(time.strftime("%Y-%m-%d"))
        if dumpdir:
            dumpfile = os.path.join(dumpdir, dumpfile)
    ndocs, nfiles = db.dump(dumpfile, exclude_designs=True, progressbar=progressbar)
    click.echo(f"Dumped {ndocs} documents and {nfiles} files to '{dumpfile}'.")


@cli.command()
@click.argument("dumpfile", type=click.Path(exists=True))
@click.option(
    "--progressbar/--no-progressbar", default=True, help="Display a progressbar."
)
def undump(dumpfile, progressbar):
    "Load a Publications database .tar.gz dump file. The database must be empty."
    db = utils.load_design_documents()
    if utils.get_count(db, "publication", "year") != 0:
        raise click.ClickException(
            f"The database '{settings['DATABASE_NAME']}' is not empty."
        )
    ndocs, nfiles = db.undump(dumpfile, progressbar=progressbar)
    click.echo(f"Loaded {ndocs} documents and {nfiles} files to '{dumpfile}'.")


@cli.command()
@click.option("--email", prompt=True)
@click.option("--password")  # Get password after account existence check.
def admin(email, password):
    "Create a user account having the admin role."
    db = utils.get_db()
    try:
        with AccountSaver(db=db) as saver:
            saver.set_email(email)
            saver["owner"] = email
            if not password:
                password = click.prompt(
                    "Password", hide_input=True, confirmation_prompt=True
                )
            saver.set_password(password)
            saver["role"] = constants.ADMIN
            saver["labels"] = []
    except ValueError as error:
        raise click.ClickException(str(error))
    click.echo(f"Created 'admin' role account {email}")


@cli.command()
@click.option("--email", prompt=True)
@click.option("--password")  # Get password after account existence check.
def curator(email, password):
    "Create a user account having the curator role."
    db = utils.get_db()
    try:
        with AccountSaver(db=db) as saver:
            saver.set_email(email)
            saver["owner"] = email
            if not password:
                password = click.prompt(
                    "Password", hide_input=True, confirmation_prompt=True
                )
            saver.set_password(password)
            saver["role"] = constants.CURATOR
            saver["labels"] = []
    except ValueError as error:
        raise click.ClickException(str(error))
    click.echo(f"Created 'curator' role account {email}")


@cli.command()
@click.option("--email", prompt=True)
@click.option("--password")  # Get password after account existence check.
def password(email, password):
    "Set the password for the given account."
    db = utils.get_db()
    try:
        user = utils.get_account(db, email)
    except KeyError as error:
        raise click.ClickException(str(error))
    try:
        with AccountSaver(doc=user, db=db) as saver:
            if not password:
                password = click.prompt(
                    "Password", hide_input=True, confirmation_prompt=True
                )
            saver.set_password(password)
    except ValueError as error:
        raise click.ClickException(str(error))
    click.echo(f"Password set for account {email}")


@cli.command()
@click.argument("identifier")
def show(identifier):
    """Display the JSON for the single item in the database.
    The identifier may be a PMID, DOI, email, API key, label, ISSN, ISSN-L,
    ORCID, or IUID of the document.
    """
    db = utils.get_db()
    for designname, viewname, operation in [
        ("publication", "pmid", _asis),
        ("publication", "doi", _asis),
        ("account", "email", _asis),
        ("account", "api_key", _asis),
        ("label", "normalized_value", _normalized),
        ("journal", "issn", _asis),
        ("journal", "issn_l", _asis),
        ("researcher", "orcid", _asis),
        ("blacklist", "doi", _asis),
        ("blacklist", "pmid", _asis),
    ]:
        try:
            doc = utils.get_doc(db, designname, viewname, operation(identifier))
            break
        except KeyError:
            pass
    else:
        try:
            doc = db[identifier]
        except couchdb2.NotFoundError:
            raise click.ClickException("No such item in the database.")
    click.echo(json.dumps(doc, ensure_ascii=False, indent=2))


def _asis(value):
    return value


def _normalized(value):
    return utils.to_ascii(value).lower()


@cli.command()
@click.option(
    "-y", "--year", "years", help="The 'published' year of publications.", multiple=True
)
@click.option(
    "-l", "--label", "labels", help="Label for the publications.", multiple=True
)
@click.option(
    "-a",
    "--author",
    "authors",
    help="Publications author name, optionally with a wildcard '*' at the end.",
    multiple=True,
)
@click.option(
    "-o",
    "--orcid",
    "orcids",
    help="Publications associated with a researcher ORCID.",
    multiple=True,
)
@click.option(
    "-x",
    "--expression",
    help="Evaluate the selection expression in the named file."
    " If any other selection options are given, the expression"
    " is evaluated for that subset.",
)
@click.option(
    "--format",
    help="Format of the output. Default CSV.",
    default="CSV",
    type=click.Choice(["CSV", "XLSX", "TXT"], case_sensitive=False),
)
@click.option("-f", "--filepath", help="Path of the output file. Use '-' for stdout.")
@click.option(
    "--all-authors/--few-authors",
    default=False,
    help="Include all authors in output; default first and last few.",
)
@click.option(
    "--issn/--no-issn", default=False, help="Include journal ISSN and ISSN-L in output."
)
@click.option("--encoding", default="utf-8", help="Character encoding; default utf-8.")
@click.option(
    "--delimiter",
    default="comma",
    type=click.Choice(["comma", "semi-colon", "tab"], case_sensitive=False),
    help="CSV: Delimiter between parts in record.",
)
@click.option(
    "--quoting",
    help="CSV: Quoting scheme.",
    default="nonnumeric",
    type=click.Choice(["all", "minimal", "nonnumeric", "none"], case_sensitive=False),
)
@click.option(
    "--single-label/--multi-label",
    default=False,
    help="CSV, XLSX: Output one single label per record;"
    " default is all labels in one record.",
)
@click.option(
    "--numbered/--not-numbered", default=False, help="TXT: Number for each item."
)
@click.option(
    "--maxline", type=int, default=None, help="TXT: Max length of each line in output."
)
@click.option("--doi-url/--no-doi-url", default=False, help="TXT: Output URL for DOI.")
@click.option(
    "--pmid-url/--no-pmid-url", default=False, help="TXT: Output URL for PMID."
)
def select(
    years,
    labels,
    authors,
    orcids,
    expression,
    format,
    filepath,
    all_authors,
    issn,
    encoding,
    delimiter,
    quoting,
    single_label,
    numbered,
    maxline,
    doi_url,
    pmid_url,
):
    """Select a subset of publications and output to a file.
    The options '--year', '--label' and '--orcid' may be given multiple
    times, giving the union of publications within the option type.
    These separate sets are the intersected to give the final subset.
    """
    db = utils.get_db()
    app = publications.app_publications.get_application()
    subsets = []

    def _union(s, t):
        return s | t

    if years:
        subsets.append(functools.reduce(_union, [Subset(db, year=y) for y in years]))
    if labels:
        subsets.append(functools.reduce(_union, [Subset(db, label=l) for l in labels]))
    if orcids:
        subsets.append(functools.reduce(_union, [Subset(db, orcid=o) for o in orcids]))
    if authors:
        subsets.append(
            functools.reduce(_union, [Subset(db, author=a) for a in authors])
        )
    if subsets:
        result = functools.reduce(lambda s, t: s & t, subsets)
    else:
        result = Subset(db)

    if expression:
        parser = get_parser()
        try:
            with open(expression) as infile:
                parsed = parser.parseString(infile.read(), parseAll=True)
        except IOError as error:
            raise click.ClickException(str(error))
        except pp.ParseException as error:
            raise click.ClickException(f"Expression invalid: {error}")
        try:
            subset = parsed[0].evaluate(db)
        except Exception as error:
            raise click.ClickException(f"Evaluating selection expression: {error}")
        if subsets:  # Were any previous subset(s) defined?
            result = result & subset
        else:
            result = subset

    if format == "CSV":
        writer = publications.writer.CsvWriter(
            db,
            app,
            all_authors=all_authors,
            single_label=single_label,
            issn=issn,
            encoding=encoding,
            quoting=quoting,
            delimiter=delimiter,
        )
        writer.write(result)
        filepath = filepath or "publications.csv"

    elif format == "XLSX":
        if filepath == "-":
            raise click.ClickException("Cannot output XLSX to stdout.")
        writer = publications.writer.XlsxWriter(
            db,
            app,
            all_authors=all_authors,
            single_label=single_label,
            issn=issn,
            encoding=encoding,
        )
        writer.write(result)
        filepath = filepath or "publications.xlsx"

    elif format == "TXT":
        writer = publications.writer.TextWriter(
            db,
            app,
            all_authors=all_authors,
            issn=issn,
            encoding=encoding,
            numbered=numbered,
            maxline=maxline,
            doi_url=doi_url,
            pmid_url=pmid_url,
        )
        writer.write(result)
        filepath = filepath or "publications.txt"

    if filepath == "-":
        sys.stdout.write(writer.get_content().decode(encoding))
    elif filepath:
        with open(filepath, "wb") as outfile:
            outfile.write(writer.get_content())
        click.echo(result)


@cli.command()
@click.option(
    "-f",
    "--filepath",
    required=True,
    help="Path of the file containing PMIDs and/or DOIs to fetch.",
)
@click.option(
    "-l",
    "--label",
    help="Optional label to add to the publications."
    " May contain a qualifier after slash '/' character.",
)
def fetch(filepath, label):
    """Fetch publications given a file containing PMIDs and/or DOIs,
    one per line. If the publication is already in the database, the label,
    if given, is added. For a PMID, the publication is fetched from PubMed.
    For a DOI, an attempt is first made to get the publication from PubMed.
    If that does not work, Crossref is tried.
    Delay, timeout and API key for fetching is defined in the settings file.
    """
    db = utils.get_db()
    identifiers = []
    try:
        with open(filepath) as infile:
            for line in infile:
                try:
                    identifiers.append(line.strip().split()[0])
                except IndexError:
                    pass
    except IOError as error:
        raise click.ClickException(str(error))
    if label:
        parts = label.split("/", 1)
        if len(parts) == 2:
            label = parts[0]
            qualifier = parts[1]
        else:
            qualifier = None
        try:
            label = utils.get_label(db, label)["value"]
        except KeyError as error:
            raise click.ClickException(str(error))
        if qualifier and qualifier not in settings["SITE_LABEL_QUALIFIERS"]:
            raise click.ClickException(f"No such label qualifier {qualifier}.")
        labels = {label: qualifier}
    else:
        labels = {}
    # All labels are allowed from the CLI; as if admin were logged in.
    allowed_labels = set([l["value"] for l in utils.get_docs(db, "label", "value")])
    for identifier in identifiers:
        try:
            publ = utils.get_publication(db, identifier)
        except KeyError:
            try:
                publ = fetch_publication(
                    db,
                    identifier,
                    labels=labels,
                    account=get_account(),
                    allowed_labels=allowed_labels,
                )
            except IOError as error:
                click.echo(f"Error: {error}")
            except KeyError as error:
                click.echo(f"Warning: {error}")
            else:
                click.echo(f"Fetched {publ['title']}")
        else:
            if add_label_to_publication(db, publ, label, qualifier):
                click.echo(f"{identifier} already in database; label updated.")
            else:
                click.echo(f"{identifier} already in database.")


@cli.command()
@click.option(
    "-l",
    "--label",
    required=True,
    help="The label to add to the publications."
    " May contain a qualifier after slash '/' character.",
)
@click.option(
    "-f",
    "--csvfilepath",
    required=True,
    help="Path of CSV file of publications to add the label to."
    " Only the IUID column in the CSV file is used.",
)
def add_label(label, csvfilepath):
    """Add a label to a set of publications."""
    db = utils.get_db()
    parts = label.split("/", 1)
    if len(parts) == 2:
        label = parts[0]
        qualifier = parts[1]
    else:
        qualifier = None
    try:
        label = utils.get_label(db, label)["value"]
    except KeyError as error:
        raise click.ClickException(str(error))
    if qualifier and qualifier not in settings["SITE_LABEL_QUALIFIERS"]:
        raise click.ClickException(f"No such label qualifier {qualifier}.")
    count = 0
    for iuid in get_iuids_from_csv(csvfilepath):
        try:
            publ = db[iuid]
        except KeyError:
            click.echo(f"No such publication {iuid}; skipping.")
        else:
            if add_label_to_publication(db, publ, label, qualifier):
                count += 1
    click.echo(f"Added label to {count} publications.")


@cli.command()
@click.option(
    "-l", "--label", required=True, help="The label to remove from the publications."
)
@click.option(
    "-f",
    "--csvfilepath",
    required=True,
    help="Path of CSV file of publications to add the label to."
    " Only the IUID column in the CSV file is used.",
)
def remove_label(label, csvfilepath):
    "Remove a label from a set of publications."
    db = utils.get_db()
    try:
        label = utils.get_label(db, label)["value"]
    except KeyError as error:
        raise click.ClickException(str(error))
    count = 0
    for iuid in get_iuids_from_csv(csvfilepath):
        try:
            publ = db[iuid]
        except KeyError:
            click.echo(f"No such publication {iuid}; skipping.")
            continue
        if label not in publ["labels"]:
            continue
        with PublicationSaver(doc=publ, db=db, account=get_account()) as saver:
            labels = publ["labels"].copy()
            labels.pop(label)
            saver["labels"] = labels
        count += 1
    click.echo(f"Removed label from {count} publications.")


@cli.command()
@click.option(
    "-f", "--filepath", default="xrefs.csv", help="Path of the output CSV file."
)
def xrefs(filepath):
    """Output all xrefs as CSV data to the given file.
    The db and key of the xref form the first two columnds.
    If a URL is defined, it is written to the third column.
    """
    db = utils.get_db()
    dbs = dict()
    for publication in utils.get_docs(db, "publication", "modified"):
        for xref in publication.get("xrefs", []):
            dbs.setdefault(xref["db"], set()).add(xref["key"])
    with open(filepath, "w") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(["db", "key", "url"])
        count = 0
        for db, keys in sorted(dbs.items()):
            for key in sorted(keys):
                row = [db, key]
                try:
                    url = settings["XREF_TEMPLATE_URLS"][db.lower()]
                    if "%-s" in url:  # Use lowercase key
                        url.replace("%-s", "%s")
                        key = key.lower()
                    row.append(url % key)
                except KeyError:
                    pass
                writer.writerow(row)
                count += 1
    click.echo(f"{count} xrefs")


@cli.command()
@click.option(
    "-f",
    "--csvfilepath",
    required=True,
    help="Path of CSV file of publications to add the label to."
    " Only the IUID column in the CSV file is used.",
)
def update_pubmed(csvfilepath):
    """Use PubMed to update the publications in the CSV file.
    If a publication lacks PMID then that publication is skipped.

    Note that a delay is inserted between each call to PubMed to avoid
    bad behaviour towards the web service.
    """
    db = utils.get_db()
    count = 0
    iuids = get_iuids_from_csv(csvfilepath)
    click.echo(f"{len(iuids)} publications in CSV input file.")
    for iuid in iuids:
        try:
            publ = db[iuid]
        except KeyError:
            click.echo(f"No such publication {iuid}; skipping.")
            continue
        pmid = publ.get("pmid")
        if not pmid:
            continue
        try:
            new = pubmed.fetch(
                pmid,
                timeout=settings["PUBMED_TIMEOUT"],
                delay=settings["PUBMED_DELAY"],
                api_key=settings["NCBI_API_KEY"],
            )
        except (OSError, IOError):
            click.echo(f"No response from PubMed for {pmid}.")
        except ValueError as error:
            click.echo(f"{pmid}, {error}")
        else:
            with PublicationSaver(doc=publ, db=db, account=get_account()) as saver:
                saver.update(new)
                saver.fix_journal()
            click.echo(f"Updated {iuid} {publ['title'][:50]}...")
            count += 1
    click.echo(f"Updated {count} publications from PubMed.")


@cli.command()
@click.option(
    "-f",
    "--csvfilepath",
    required=True,
    help="Path of CSV file of publications to add the label to."
    " Only the IUID column in the CSV file is used.",
)
def update_crossref(csvfilepath):
    """Use Crossref to update the publications in the CSV file.
    If a publication lacks DOI then that publication is skipped.

    Note that a delay is inserted between each call to Crossref to avoid
    bad behaviour towards the web service.
    """
    db = utils.get_db()
    count = 0
    iuids = get_iuids_from_csv(csvfilepath)
    click.echo(f"{len(iuids)} publications in CSV input file.")
    for iuid in iuids:
        try:
            publ = db[iuid]
        except KeyError:
            click.echo(f"No such publication {iuid}; skipping.")
            continue
        doi = publ.get("doi")
        if not doi:
            continue
        try:
            new = crossref.fetch(
                doi,
                timeout=settings["CROSSREF_TIMEOUT"],
                delay=settings["CROSSREF_DELAY"],
            )
        except (OSError, IOError):
            click.echo(f"No response from Crossref for {doi}.")
        except ValueError as error:
            click.echo(f"{doi}, {error}")
        else:
            with PublicationSaver(doc=publ, db=db, account=get_account()) as saver:
                saver.update(new)
                saver.fix_journal()
            click.echo(f"Updated {iuid} {publ['title'][:50]}...")
            count += 1
    click.echo(f"Updated {count} publications from Crossref.")


@cli.command()
@click.option(
    "-f",
    "--csvfilepath",
    required=True,
    help="Path of CSV file of publications to add the label to."
    " Only the IUID column in the CSV file is used.",
)
def find_pmid(csvfilepath):
    """Find the PMID for the publications in the CSV file.
    Search by DOI and title.

    Note that a delay is inserted between each call to PubMed to avoid
    bad behaviour towards the web service.
    """
    db = utils.get_db()
    count = 0
    iuids = get_iuids_from_csv(csvfilepath)
    click.echo(f"{len(iuids)} publications in CSV input file.")
    for iuid in iuids:
        try:
            publ = db[iuid]
        except KeyError:
            click.echo(f"No such publication {iuid}; skipping.")
            continue
        if publ.get("pmid"):
            continue
        doi = publ.get("doi")
        if doi:
            result = pubmed.search(doi=doi)
        else:
            result = pubmed.search(title=publ["title"])
        if len(result) == 1:
            with PublicationSaver(doc=publ, db=db, account=get_account()) as saver:
                saver["pmid"] = result[0]
            click.echo(f"PMID {result[0]}: {publ['title'][:50]}...")
            count += 1
    click.echo(f"Set PMID for {count} publications.")


def add_label_to_publication(db, publication, label, qualifier):
    if publication["labels"].get(label, "dummy qualifier") == qualifier:
        return False
    with PublicationSaver(doc=publication, db=db, account=get_account()) as saver:
        labels = publication["labels"].copy()
        labels[label] = qualifier
        saver["labels"] = labels
    return True


def get_iuids_from_csv(csvfilepath):
    try:
        with open(csvfilepath) as infile:
            reader = csv.DictReader(infile)
            return [p["IUID"] for p in reader]
    except (IOError, csv.Error, KeyError) as error:
        raise click.ClickException(str(error))

def get_account():
    "Get dict with current account info for logging purposes."
    try:
        email = os.getlogin()
    except OSError:
        email = "unknown"
    return {"email": email, "user_agent": "CLI"}


if __name__ == "__main__":
    cli()
