"Various utility functions."

import datetime
import email.message
import hashlib
import smtplib
import string
import uuid
import unicodedata

import couchdb2
import marko

from publications import constants
from publications import settings

import publications.database


def get_iuid():
    "Return a unique instance identifier."
    return uuid.uuid4().hex


def hashed_password(password):
    "Return the password in hashed form."
    sha256 = hashlib.sha256(settings["PASSWORD_SALT"].encode("utf-8"))
    sha256.update(password.encode("utf-8"))
    return sha256.hexdigest()


def check_password(password):
    """Check that the password is long and complex enough.
    Raise ValueError otherwise."""
    if len(password) < settings["MIN_PASSWORD_LENGTH"]:
        raise ValueError(
            "Password must be at least {0} characters.".format(
                settings["MIN_PASSWORD_LENGTH"]
            )
        )


def timestamp(days=None):
    """Current date and time (UTC) in ISO format, with millisecond precision.
    Add the specified offset in days, if given.
    """
    instant = datetime.datetime.utcnow()
    if days:
        instant += datetime.timedelta(days=days)
    instant = instant.isoformat()
    return instant[:17] + "%06.3f" % float(instant[17:]) + "Z"


def epoch_to_iso(epoch):
    """Convert the given number of seconds since the epoch
    to date and time in ISO format.
    """
    dt = datetime.datetime.fromtimestamp(float(epoch))
    return dt.isoformat() + "Z"


def today(days=None):
    """Current date (UTC) in ISO format.
    Add the specified offset in days, if given.
    """
    instant = datetime.datetime.utcnow()
    if days:
        instant += datetime.timedelta(days=days)
    result = instant.isoformat()
    return result[: result.index("T")]


def to_date(value):
    """Convert value to proper ISO format date.
    Return today if None.
    Raise ValueError if cannot be interpreted.
    """
    if not value:
        return today()
    result = []
    parts = value.split("-")
    try:
        year = int(parts[0])
        try:
            month = int(parts[1])
            if month < 0:
                raise ValueError
            if month > 12:
                raise ValueError
        except IndexError:
            month = 0
        try:
            day = int(parts[2])
            if day < 0:
                raise ValueError
            if day > 31:
                raise ValueError
        except IndexError:
            day = 0
    except (TypeError, ValueError):
        raise ValueError(f"invalid date '{value}'")
    return "%s-%02i-%02i" % (year, month, day)


def to_ascii(value, alphanum=False):
    """Convert any non-ASCII character to its closest ASCII equivalent.
    'alphanum': retain only alphanumerical characters and whitespace.
    """
    if value is None:
        return ""
    value = unicodedata.normalize("NFKD", str(value))
    value = "".join([c for c in value if not unicodedata.combining(c)])
    if alphanum:
        alphanum = set(string.ascii_letters + string.digits + string.whitespace)
        value = "".join([c for c in value if c in alphanum])
    return value


def squish(value):
    "Remove all unnecessary white spaces."
    return " ".join([p for p in value.split() if p])


def to_bool(value):
    "Convert the value into a boolean, interpreting various string values."
    if isinstance(value, bool):
        return value
    if not value:
        return False
    lowvalue = value.lower()
    if lowvalue in constants.TRUE:
        return True
    if lowvalue in constants.FALSE:
        return False
    raise ValueError("invalid boolean: '{value}'")


def strip_prefix(value):
    "Strip any prefix from the string value."
    value = value.strip()
    lowcase = value.lower()
    for prefix in constants.IDENTIFIER_PREFIXES:
        if lowcase.startswith(prefix):
            return value[len(prefix) :].strip()
    return value


def get_formatted_authors(authors, complete=False):
    "Get formatted list of authors; partial or complete list."
    if (
        not complete
        and len(authors)
        > settings["NUMBER_FIRST_AUTHORS"] + settings["NUMBER_LAST_AUTHORS"]
    ):
        authors = (
            authors[: settings["NUMBER_FIRST_AUTHORS"]]
            + [None]
            + authors[-settings["NUMBER_LAST_AUTHORS"] :]
        )
    result = []
    for author in authors:
        if author:
            name = "%s %s" % (
                " ".join((author["family"] or "").split()),
                author.get("initials") or "",
            )
            # Get rid of bizarre newlines in author names.
            result.append(" ".join(name.strip().split()))
        else:
            result.append("...")
    return ", ".join(result)


class EmailServer:
    "A connection to an email server for sending emails."

    def __init__(self):
        """Open the connection to the email server.
        Raise ValueError if no email server host has been defined
        or any other problem.
        """
        try:
            server = settings["MAIL_SERVER"]
            if not server:
                raise KeyError
            self.email = settings["MAIL_DEFAULT_SENDER"] or settings["MAIL_USERNAME"]
            if not self.email:
                raise KeyError
            port = int(settings["MAIL_PORT"])
            use_ssl = to_bool(settings["MAIL_USE_SSL"])
            use_tls = to_bool(settings["MAIL_USE_TLS"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("email server is not properly defined")
        try:
            if use_tls:
                self.server = smtplib.SMTP(server, port=port)
                if settings.get("MAIL_EHLO"):
                    self.server.ehlo(settings["MAIL_EHLO"])
                self.server.starttls()
                if settings.get("MAIL_EHLO"):
                    self.server.ehlo(settings["MAIL_EHLO"])
            elif use_ssl:
                self.server = smtplib.SMTP_SSL(server, port=port)
            else:
                self.server = smtplib.SMTP(server, port=port)
            try:
                username = settings["MAIL_USERNAME"]
                if not username:
                    raise KeyError
                password = settings["MAIL_PASSWORD"]
                if not password:
                    raise KeyError
            except KeyError:
                pass
            else:
                self.server.login(username, password)
        except smtplib.SMTPException as error:
            raise ValueError(str(error))

    def __del__(self):
        "Close the connection to the email server."
        try:
            self.server.quit()
        except (smtplib.SMTPException, AttributeError):
            pass

    def send(self, recipient, subject, text):
        "Send an email."
        try:
            message = email.message.EmailMessage()
            message["From"] = self.email
            message["Subject"] = subject
            if settings["MAIL_REPLY_TO"]:
                message["Reply-to"] = settings["MAIL_REPLY_TO"]
            message["To"] = recipient
            message.set_content(text)
            self.server.send_message(message)
        except smtplib.SMTPException as error:
            raise ValueError(str(error))


def markdown2html(text, safe=False):
    "Process the text from Markdown to HTML."
    text = text or ""
    if not safe:
        text = tornado.escape.xhtml_escape(text)
    return marko.Markdown(renderer=HtmlRenderer).convert(text or "")


class HtmlRenderer(marko.html_renderer.HTMLRenderer):
    "Extension of Marko Markdown-to-HTML renderer."

    def render_link(self, element):
        """Allow setting <a> attribute '_target' to '_blank', when the title
        begins with an exclamation point '!'.
        """
        if element.title and element.title.startswith("!"):
            template = '<a target="_blank" href="{url}"{title}>{body}</a>'
            element.title = element.title[1:]
        else:
            template = '<a href="{url}"{title}>{body}</a>'
        title = (
            ' title="{}"'.format(self.escape_html(element.title))
            if element.title
            else ""
        )
        return template.format(
            url=self.escape_url(element.dest),
            title=title,
            body=self.render_children(element),
        )

    def render_heading(self, element):
        "Add id to all headings."
        id = self.get_text_only(element).replace(" ", "-").lower()
        id = "".join(c for c in id if c in constants.ALLOWED_ID_CHARACTERS)
        return '<h{level} id="{id}">{children}</h{level}>\n'.format(
            level=element.level, id=id, children=self.render_children(element)
        )

    def get_text_only(self, element):
        "Helper function to extract only the text from element and its children."
        if isinstance(element.children, str):
            return element.children
        else:
            return "".join([self.get_text_only(el) for el in element.children])
