"Command line interface to the Publications database."

import csv
import functools
import io
import json
import os
import tarfile
import time
import sys

import couchdb2
import click

from publications import constants
from publications import crossref
from publications import designs
from publications import pubmed
from publications import settings
from publications import utils
from publications.account import AccountSaver
from publications.publication import PublicationSaver, fetch_publication
from publications.subset import Subset, get_parser
import publications.app_publications
import publications.writer


@click.group()
@click.option("-s", "--settings", help="Name of settings YAML file.")
@click.option("--log", flag_value=True, default=False,
              help="Enable logging output.")
@click.pass_context
def cli(ctx, settings, log):
    ctx.ensure_object(dict)
    utils.load_settings(settings, log=log)
    ctx.obj["db"] = utils.get_db()
    ctx.obj["app"] = publications.app_publications.get_application()

@cli.command()
@click.pass_context
def initialize(ctx):
    "Initialize the database, which must exist; load all design documents."
    db = ctx.obj["db"]
    designs.load_design_documents(db)
    click.echo("Loaded all design documents.")

@cli.command()
@click.pass_context
def counts(ctx):
    "Output counts of database entities."
    db = ctx.obj["db"]
    designs.load_design_documents(db)
    click.echo(f"{utils.get_count(db, 'publication', 'year'):>5} publications")
    click.echo(f"{utils.get_count(db, 'label', 'value'):>5} labels")
    click.echo(f"{utils.get_count(db, 'account', 'email'):>5} accounts")
    click.echo(f"{utils.get_count(db, 'researcher', 'name'):>5} researchers")

@cli.command()
@click.option("-d", "--dumpfile", type=str,
                help="The path of the Publications database dump file.")
@click.option("-D", "--dumpdir", type=str,
                help="The directory to write the dump file in, using the standard name.")
@click.pass_context
def dump(ctx, dumpfile, dumpdir):
    "Dump all data in the database to a .tar.gz dump file."
    db = ctx.obj["db"]
    if not dumpfile:
        dumpfile = "dump_{0}.tar.gz".format(time.strftime("%Y-%m-%d"))
        if dumpdir:
            filepath = os.path.join(dumpdir, dumpfile)
    count_items = 0
    count_files = 0
    if dumpfile.endswith(".gz"):
        mode = "w:gz"
    else:
        mode = "w"
    with tarfile.open(dumpfile, mode=mode) as outfile:
        with click.progressbar(db, label="Dumping...") as bar:
            for doc in bar:
                # Only documents that explicitly belong to the application.
                if doc.get(constants.DOCTYPE) is None: continue
                del doc["_rev"]
                info = tarfile.TarInfo(doc["_id"])
                data = json.dumps(doc).encode("utf-8")
                info.size = len(data)
                outfile.addfile(info, io.BytesIO(data))
                count_items += 1
                for attname in doc.get("_attachments", dict()):
                    info = tarfile.TarInfo("{0}_att/{1}".format(doc["_id"], attname))
                    attfile = db.get_attachment(doc, attname)
                    if attfile is None: continue
                    data = attfile.read()
                    attfile.close()
                    info.size = len(data)
                    outfile.addfile(info, io.BytesIO(data))
                    count_files += 1
    click.echo(f"Dumped {count_items} items and {count_files} files to {dumpfile}")

@cli.command()
@click.argument("dumpfile", type=click.Path(exists=True))
@click.pass_context
def undump(ctx, dumpfile):
    "Load a Publications database .tar.gz dump file. The database must be empty."
    db = ctx.obj["db"]
    designs.load_design_documents(db)
    if utils.get_count(db, 'publication', 'year') != 0:
        raise click.ClickException(f"The {settings['DATABASE_NAME']} database is not empty.")
    count_items = 0
    count_files = 0
    attachments = dict()
    with tarfile.open(dumpfile, mode="r") as infile:
        length = sum(1 for member in infile if member.isreg())
    with tarfile.open(dumpfile, mode="r") as infile:
        with click.progressbar(infile, label="Loading...", length=length) as bar:
            for item in bar:
                itemfile = infile.extractfile(item)
                itemdata = itemfile.read()
                itemfile.close()
                if item.name in attachments:
                    # This relies on an attachment being after its item in the tarfile.
                    db.put_attachment(doc, itemdata, **attachments.pop(item.name))
                    count_files += 1
                else:
                    doc = json.loads(itemdata)
                    atts = doc.pop("_attachments", dict())
                    db.put(doc)
                    count_items += 1
                    for attname, attinfo in list(atts.items()):
                        key = "{0}_att/{1}".format(doc["_id"], attname)
                        attachments[key] = dict(filename=attname,
                                                content_type=attinfo["content_type"])
    click.echo(f"Loaded {count_items} items and {count_files} files.")
    
@cli.command()
@click.option("--email", prompt=True)
@click.option("--password")     # Get password after account existence check.
@click.pass_context
def admin(ctx, email, password):
    "Create a user account having the admin role."
    db = ctx.obj["db"]
    try:
        with AccountSaver(db=db) as saver:
            saver.set_email(email)
            saver['owner'] = email
            if not password:
                password = click.prompt("Password", 
                                        hide_input=True,
                                        confirmation_prompt=True)
            saver.set_password(password)
            saver['role'] = constants.ADMIN
            saver['labels'] = []
    except ValueError as error:
        raise click.ClickException(str(error))
    click.echo(f"Created 'admin' role account {email}")
    
@cli.command()
@click.option("--email", prompt=True)
@click.option("--password")     # Get password after account existence check.
@click.pass_context
def curator(ctx, email, password):
    "Create a user account having the curator role."
    db = ctx.obj["db"]
    try:
        with AccountSaver(db=db) as saver:
            saver.set_email(email)
            saver['owner'] = email
            if not password:
                password = click.prompt("Password", 
                                        hide_input=True,
                                        confirmation_prompt=True)
            saver.set_password(password)
            saver['role'] = constants.CURATOR
            saver['labels'] = []
    except ValueError as error:
        raise click.ClickException(str(error))
    click.echo(f"Created 'curator' role account {email}")
    
@cli.command()
@click.option("--email", prompt=True)
@click.option("--password")     # Get password after account existence check.
@click.pass_context
def password(ctx, email, password):
    "Set the password for the given account."
    db = ctx.obj["db"]
    try:
        user = utils.get_account(db, email)
    except KeyError as error:
        raise click.ClickException(str(error))
    try:
        with AccountSaver(doc=user, db=db) as saver:
            if not password:
                password = click.prompt("Password", 
                                        hide_input=True,
                                        confirmation_prompt=True)
            saver.set_password(password)
    except ValueError as error:
        raise click.ClickException(str(error))
    click.echo(f"Password set for account {email}")

@cli.command()
@click.argument("identifier")
@click.pass_context
def show(ctx, identifier):
    """Display the JSON for the single item in the database.
    The identifier may be a PMID, DOI, email, API key, label, ISSN, ISSN-L,
    ORCID, or IUID of the document.
    """
    db = ctx.obj["db"]
    for designname, viewname, operation in [("publication", "pmid", asis),
                                            ("publication", "doi", asis),
                                            ("account", "email", asis),
                                            ("account", "api_key", asis),
                                            ("label", "normalized_value", normalized),
                                            ("journal", "issn", asis),
                                            ("journal", "issn_l", asis),
                                            ("researcher", "orcid", asis),
                                            ("blacklist", "doi", asis),
                                            ("blacklist", "pmid", asis)]:
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
    click.echo(json_dumps(doc))

@cli.command()
@click.option("-y", "--year", "years",
              help="The 'published' year of publications.", multiple=True)
@click.option("-l", "--label", "labels",
              help="Label for the publications.", multiple=True)
@click.option("-a", "--author", "authors",
              help="Publications author name, optionally with a wildcard '*' at the end.",
              multiple=True)
@click.option("-o", "--orcid", "orcids",
              help="Publications associated with a researcher ORCID.",
              multiple=True)
@click.option("-x", "--expression",
              help="Evaluate the selection expression in the named file."
              " If any other selection options are given, the expression"
              " is evaluated for that subset.")
@click.option("--format", help="Format of the output.",
              default="CSV",
              type=click.Choice(["CSV", "XLSX", "TEXT", "TXT"],
                                case_sensitive=False))
@click.option("--filepath", help="Path of the output file. Use '-' for stdout.")
@click.option("--quoting", help="CSV only: Quoting scheme to use.",
              default="nonnumeric",
              type=click.Choice(["all", "minimal", "nonnumeric", "none"],
                                case_sensitive=False))
# XXX format: numbered, maxline, issn, single_label, encoding, doi_url, pmid_url
@click.pass_context
def select(ctx, years, labels, authors, orcids, expression,
           format, filepath, quoting):
    """Select a subset of publications and output to a file.
    The options '--year', '--label' and '--orcid' may be given multiple 
    times, giving the union of publications within the option type.
    These separate sets are the intersected to give the final subset.
    """
    db = ctx.obj["db"]
    subsets = []
    if years:
        subsets.append(
            functools.reduce(union, [Subset(db, year=y) for y in years]))
    if labels:
        subsets.append(
            functools.reduce(union, [Subset(db, label=l) for l in labels]))
    if orcids:
        subsets.append(
            functools.reduce(union, [Subset(db, orcid=o) for o in orcids]))
    if authors:
        subsets.append(
            functools.reduce(union, [Subset(db,author=a) for a in authors]))
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
        if subsets:             # Were any previous subset(s) defined?
            result = result & subset
        else:
            result = subset

    if format == "CSV":
        writer = publications.writer.CsvWriter(db, ctx.obj["app"],
                                               quoting=quoting)
        writer.write(result)
        filepath = filepath or "publications.csv"

    elif format == "XLSX":
        if filepath == "-":
            raise click.ClickException("Cannot output XLSX to stdout.")
        writer = publications.writer.XlsxWriter(db, ctx.obj["app"])
        writer.write(result)
        filepath = filepath or "publications.xlsx"

    elif format in ("TEXT", "TXT"):
        writer = publications.writer.TextWriter(db, ctx.obj["app"])
        writer.write(result)
        filepath = filepath or "publications.txt"

    if filepath == "-":
        sys.stdout.write(writer.get_content().decode("utf-8"))
    elif filepath:
        with open(filepath, "wb") as outfile:
            outfile.write(writer.get_content())
        click.echo(result)

@cli.command()
@click.option("-f", "--filepath", required=True,
              help="Path of the file containing PMIDs and/or DOIs to fetch.")
@click.option("-l", "--label", help="Optional label to add to the publications."
              " May contain a qualifier after slash '/' character.")
@click.pass_context
def fetch(ctx, filepath, label):
    """Fetch publications given a file containing PMIDs and/or DOIs,
    one per line. If the publication is already in the database, the label,
    if given, is added. For a PMID, the publication is fetched from PubMed.
    For a DOI, an attempt is first made to get the publication from PubMed.
    If that does not work, Crossref is tried.
    Delay, timeout and API key for fetching is defined in the settings file.
    """
    db = ctx.obj["db"]
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
    account = {"email": os.getlogin(), "user_agent": "CLI"}
    allowed_labels = set([l["value"]
                          for l in utils.get_docs(db, "label", "value")])
    for identifier in identifiers:
        try:
            publ = utils.get_publication(db, identifier)
        except KeyError:
            try:
                publ = fetch_publication(db, identifier,
                                         labels=labels, account=account,
                                         allowed_labels=allowed_labels)
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
@click.option("-l", "--label", required=True,
              help="The label to add to the publications."
              " May contain a qualifier after slash '/' character.")
@click.option("-f", "--csvfilepath", required=True,
              help="Path of CSV file of publications to add the label to."
              " Only the IUID column in the CSV file is used.")
@click.pass_context
def add_label(ctx, label, csvfilepath):
    """Add a label to a set of publications.
    """
    db = ctx.obj["db"]
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
            click.echo(f"No such publication '{iuid}'; skipping.")
        else:
            if add_label_to_publication(db, publ, label, qualifier):
                count += 1
    click.echo(f"Added label to {count} publications.")

@cli.command()
@click.option("-l", "--label", required=True,
              help="The label to remove from the publications.")
@click.option("-f", "--csvfilepath", required=True,
              help="Path of CSV file of publications to add the label to."
              " Only the IUID column in the CSV file is used.")
@click.pass_context
def remove_label(ctx, label, csvfilepath):
    """Remove a label from a set of publications.
    """
    db = ctx.obj["db"]
    try:
        label = utils.get_label(db, label)["value"]
    except KeyError as error:
        raise click.ClickException(str(error))
    count = 0
    for iuid in get_iuids_from_csv(csvfilepath):
        try:
            publ = db[iuid]
        except KeyError:
            click.echo(f"No such publication '{iuid}'; skipping.")
            continue
        if label not in publ["labels"]: continue
        account = {"email": os.getlogin(), "user_agent": "CLI"}
        with PublicationSaver(doc=publ, db=db, account=account) as saver:
            labels = publ['labels'].copy()
            labels.pop(label)
            saver['labels'] = labels
        count += 1
    click.echo(f"Removed label from {count} publications.")


def add_label_to_publication(db, publication, label, qualifier):
    if publication["labels"].get(label, "dummy qualifier") == qualifier:
        return False
    account = {"email": os.getlogin(), "user_agent": "CLI"}
    with PublicationSaver(doc=publication, db=db, account=account) as saver:
        labels = publication['labels'].copy()
        labels[label] = qualifier
        saver['labels'] = labels
    return True

def get_iuids_from_csv(csvfilepath):
    try:
        with open(csvfilepath) as infile:
            reader = csv.DictReader(infile)
            return [p["IUID"] for p in reader]
    except (IOError, csv.Error, KeyError) as error:
        raise click.ClickException(str(error))

def union(s, t): return s | t

def json_dumps(doc): return json.dumps(doc, ensure_ascii=False, indent=2)

def asis(value): return value

def normalized(value): return utils.to_ascii(value).lower()


if __name__ == "__main__":
    cli()
