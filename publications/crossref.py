"Crossref interface."

import json
import os.path
import re
import sys
import time
import unicodedata

import requests

CROSSREF_FETCH_URL = "https://api.crossref.org/works/%s"

DEFAULT_TIMEOUT = 5.0
DEFAULT_DELAY = 0.5

MARKUP_RX = re.compile(r"<(/?.{1,6})>")
ORCID_RX = re.compile(r"^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[X0-9]$")


def fetch(doi, dirname=None, timeout=DEFAULT_TIMEOUT, delay=DEFAULT_DELAY, debug=False):
    """Fetch publication JSON data from Crossref and parse into a dictionary.
    Raise IOError if no connection or timeout.
    Use the file cache directory if given.
    Delay the HTTP request if positive value (seconds).
    """
    filename = doi.replace("/", "_") + ".json"
    data = None
    if dirname:
        try:
            with open(os.path.join(dirname, filename)) as infile:
                data = json.load(infile)
        except IOError:
            pass
    if not data:
        url = CROSSREF_FETCH_URL % doi
        if delay > 0.0:
            time.sleep(delay)
        if debug:
            print("url>", url)
        try:
            response = requests.get(url, timeout=timeout)
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError):
            raise IOError("timeout")
        if response.status_code != 200:
            raise IOError(f"HTTP status {response.status_code} {url}")
        data = response.json()
        # Store the JSON file locally.
        if dirname:
            with open(os.path.join(dirname, filename), "w") as outfile:
                outfile.write(json.dumps(data, indent=2, ensure_ascii=False))
    return parse(data)


def parse(data):
    "Parse JSON data for a publication into a dictionary."
    result = dict()
    result["title"] = squish(remove_markup(get_title(data)))
    result["doi"] = get_doi(data)
    result["pmid"] = get_pmid(data)
    result["authors"] = get_authors(data)
    result["journal"] = get_journal(data)
    result["type"] = get_type(data)
    result["published"] = get_published(data)
    result["epublished"] = get_epublished(data)
    result["abstract"] = get_abstract(data)
    result["xrefs"] = get_xrefs(data)
    return result


def get_title(data):
    "Get the title from the article JSON."
    try:
        return " ".join(data["message"]["title"])
    except KeyError:
        for item in data["message"]["assertion"]:
            if item["name"] == "articletitle":
                return item["value"]


def get_doi(data):
    "Get the DOI from the article JSON."
    return data["message"]["DOI"]


def get_pmid(data):
    "Get the PMID from the article JSON; not present."
    return None


def get_authors(data):
    "Get the list of authors from the article JSON."
    result = []
    for item in data["message"].get("author", []):
        author = dict()
        author["family"] = item.get("family")
        # May be lacking for consortia and such; give up.
        if not author["family"]:
            continue
        author["family_normalized"] = to_ascii(author["family"]).lower()
        # Remove dots and dashes
        given = item.get("given", "").replace(".", " ").replace("-", " ")
        # Replace weird blank characters
        author["given"] = " ".join(given.split())
        author["given_normalized"] = to_ascii(author["given"]).lower()
        author["initials"] = "".join([n[0] for n in given.split()])
        author["initials_normalized"] = to_ascii(author["initials"]).lower()
        try:
            author["orcid"] = normalize_orcid(item["ORCID"])
        except KeyError:
            pass
        author["affiliations"] = []
        for affiliation in item.get("affiliation") or []:
            # Affiliations are sometimes given as dictionaries...
            if isinstance(affiliation, str):
                author["affiliations"].append(affiliation)
            else:
                try:
                    author["affiliations"].append(affiliation["name"])
                except (KeyError, TypeError):
                    pass
        result.append(author)
    return result


def get_journal(data):
    "Get the journal data from the article JSON."
    result = dict()
    try:
        result["title"] = " ".join(data["message"]["short-container-title"])
    except KeyError:
        result["title"] = " ".join(data["message"]["container-title"])
    try:
        result["issn"] = data["message"]["ISSN"][0]
    except (KeyError, IndexError):
        result["issn"] = None
    result["volume"] = data["message"].get("volume")
    result["issue"] = data["message"].get("issue")
    result["pages"] = data["message"].get("page")
    return result


def get_type(data):
    "Get the type from the article JSON."
    try:
        return data["message"].get("type")
    except KeyError:
        return None


def get_published(data):
    "Get the print publication date from the article JSON."
    # Try in order: print, issued, created, deposited
    for key in ["published-print", "issued", "created", "deposited"]:
        try:
            item = data["message"][key]
            if item == [None]:
                raise KeyError  # Apparent dummy value
            parts = [int(i) for i in item["date-parts"][0]]
            if not parts:
                raise KeyError
        except (KeyError, TypeError, ValueError):
            pass
        else:
            # Add dummy values, if missing
            if len(parts) == 1:
                parts.append(0)
            if len(parts) == 2:
                parts.append(0)
            return "%s-%02i-%02i" % tuple(parts)
    # No such entry found; use a 'random' year.
    return "1900-0-0"


def get_epublished(data):
    "Get the online publication date from the article JSON, or None."
    # Try in order: online, issued
    for key in ["published-online", "issued"]:
        try:
            item = data["message"][key]
            parts = [int(i) for i in item["date-parts"][0]]
            if not parts:
                raise KeyError
        except (KeyError, TypeError, ValueError):
            pass
        else:
            # Add dummy values, if missing
            if len(parts) == 1:
                parts.append(0)
            if len(parts) == 2:
                parts.append(0)
            return "%s-%02i-%02i" % tuple(parts)
    return None


def get_abstract(data):
    "Get the abstract from the article JSON; not present."
    return None


def get_xrefs(data):
    "Get the list of cross-references from the article JSON; not present."
    return []


def to_ascii(value):
    "Convert any non-ASCII character to its closest ASCII equivalent."
    if value is None:
        return ""
    value = unicodedata.normalize("NFKD", str(value))
    return "".join([c for c in value if not unicodedata.combining(c)])


def remove_markup(value):
    "Remove all markup-like code, e.g. <sub> or </sub> with empty string."
    return MARKUP_RX.sub("", value)


def squish(value):
    "Remove all unnecessary white spaces."
    return " ".join([p for p in value.split() if p])


def normalize_orcid(value):
    "Try to normalize ORCID. Return None if invalid format."
    "Try to normalize ORCID. Return None if invalid format."
    if not value:
        return None
    # ORCID may be given as an URL; split away all except id proper.
    value = value.split("/")[-1].upper()
    # Remove dashes, reintroduce, test.
    value = value.replace("-", "")
    value = f"{value[0:4]}-{value[4:8]}-{value[8:12]}-{value[12:16]}"
    return value if ORCID_RX.match(value) else None
