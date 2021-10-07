"Command line interface to the Publications database."

import io
import json
import tarfile
import time
import logging

import couchdb2
import click

from publications import constants
from publications import utils
from publications import designs
from publications import settings
from publications.subset import Subset
from publications.account import AccountSaver
import publications.app_publications
import publications.writer


@click.group()
@click.option("-s", "--settings", help="Settings YAML file.")
@click.option("--log", flag_value=True, default=False, help="Enable logging.")
@click.pass_context
def cli(ctx, settings, log):
    ctx.ensure_object(dict)
    if not log:
        logging.getLogger().disabled = True
    utils.load_settings(settings)
    ctx.obj["db"] = utils.get_db()
    ctx.obj["app"] = publications.app_publications.get_application()

@cli.command()
@click.pass_context
@click.option("--force", is_flag=True, help="Initialize without confirmation.")
def initialize(ctx, force):
    """Empty and initialize the database, which must exist.
    Deletion is done the the slow way. Design documents are loaded.
    """
    if not force:
        click.confirm(f"Delete everything in database {settings['DATABASE_NAME']}",
                      abort=True)
    db = ctx.obj["db"]
    click.echo(f"Deleting all documents in the database {settings['DATABASE_NAME']}...")
    with click.progressbar(db, label="Deleting...") as bar:
        for doc in bar:
            db.delete(doc)
    designs.load_design_documents(db)
    click.echo("Deleted all documents.")

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
@click.option("--password")
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
@click.option("--password")
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
@click.option("--password")
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
              help="The year of publication.", multiple=True)
@click.option("-l", "--label", "labels",
              help="Label for the publication.", multiple=True)
@click.option("--format", help="Format of the output file.",
              default="CSV",
              type=click.Choice(["CSV", "XLSX", "TEXT"], case_sensitive=False))
@click.option("--quoting", help="Quoting scheme to use for CSV output file.",
              default="nonnumeric",
              type=click.Choice(["all", "minimal", "nonnumeric", "none"],
                                case_sensitive=False))
@click.option("--filepath", help="Path of the output file.")
@click.pass_context
def select(ctx, years, labels, format, quoting, filepath):
    """Select a subset of publications and output to a file.
    Multiple years may be provided, giving the union of such publications.
    Multiple labels may be provided, giving the union of such publications.
    If both year(s) and label(s) are given, the intersection of those two
    sets will be produced.
    """
    db = ctx.obj["db"]
    if years:
        subset_year = Subset(db, year=years[0])
        for year in years[1:]:
            subset_year = subset_year + Subset(db, year=year)
    if labels:
        subset_label = Subset(db, label=labels[0])
        for label in labels[1:]:
            subset_label = subset_label + Subset(db, label=label)
        if years:
            result = subset_year / subset_label
        else:
            result = subset_label
    else:
        result = subset_year
    if format == "CSV":
        writer = publications.writer.CsvWriter(db, ctx.obj["app"],
                                               quoting=quoting)
        writer.write(result)
        with open("publications.csv", "wb") as outfile:
            outfile.write(writer.get_content())
    elif format == "XLSX":
        writer = publications.writer.XlsxWriter(db, ctx.obj["app"])
        writer.write(result)
        with open("publications.xlsx", "wb") as outfile:
            outfile.write(writer.get_content())
    elif format == "TEXT":
        writer = publications.writer.TextWriter(db, ctx.obj["app"])
        writer.write(result)
        with open("publications.txt", "wb") as outfile:
            outfile.write(writer.get_content())
    click.echo(result)


def json_dumps(doc): return json.dumps(doc, ensure_ascii=False, indent=2)
def asis(value): return value
def normalized(value): return utils.to_ascii(value).lower()

if __name__ == "__main__":
    cli()
