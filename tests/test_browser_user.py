"""Test browser anonymous access.

After installing from PyPi using the 'requirements.txt' file, one must do:
$ playwright install

To run while displaying browser window:
$ pytest --headed

Much of the code below was created using the playwright code generation feature:
$ playwright codegen http://localhost:8885/
"""

import urllib.parse

import pytest
import playwright.sync_api

import utils


@pytest.fixture(scope="module")
def settings():
    "Get the settings from file 'settings.json' in this directory."
    return utils.get_settings(BASE_URL="http://localhost:8885",
                              USER_USERNAME=None,
                              USER_PASSWORD=None)

def login_user(settings, page):
    "Login to the system as ordinary user."
    page.goto(settings["BASE_URL"])
    page.click("text=Login")
    assert page.url == f"{settings['BASE_URL']}/login"
    page.click('input[name="email"]')
    page.fill('input[name="email"]', settings["USER_USERNAME"])
    page.press('input[name="email"]', "Tab")
    page.fill('input[name="password"]', settings["USER_PASSWORD"])
    page.click("id=login")
    assert page.url.rstrip("/") == f"{settings['BASE_URL']}"


def test_user(settings, page):
    "Test access to user page."
    login_user(settings, page)
    page.set_default_navigation_timeout(3000)

    page.click("#user")
    assert settings["USER_USERNAME"] == page.inner_text("h1").strip()


def test_fetching_publication(settings, page):
    "Test fetching a publication by PMID, and deleting it."
    login_user(settings, page)
    
    page.click("text=Publications")
    page.click("text=By fetching data")
    assert page.url == "http://localhost:8885/fetch"
    page.fill("textarea[name=\"identifiers\"]", "8142349")
    page.click("textarea[name=\"identifiers\"]")
    page.click(":nth-match(button:has-text(\"Fetch\"), 2)")
    page.click("text=Solution structure and dynamics of ras p21.GDP determined by heteronuclear three")
    url = page.url

    page.click("a[role=\"button\"]:has-text(\"1994 (1)\")")
    assert page.url == "http://localhost:8885/publications/1994"
    page.click("text=Solution structure and dynamics of ras p21.GDP determined by heteronuclear three")
    assert page.url == url

    # Try fetching it again; should not add anything.
    page.click("text=Publications")
    page.click("text=By fetching data")
    assert page.url == "http://localhost:8885/fetch"
    page.fill("textarea[name=\"identifiers\"]", "8142349")
    page.click(":nth-match(button:has-text(\"Fetch\"), 2)")
    page.click("text=Solution structure and dynamics of ras p21.GDP determined by heteronuclear three")
    assert page.url == url

    # Delete the publication.
    page.once("dialog", lambda dialog: dialog.accept())  # Callback for next click.
    page.click("text=Delete")
    assert page.url == "http://localhost:8885/"

    locator = page.locator("a[role=\"button\"]:has-text(\"1994 (1)\")")
    playwright.sync_api.expect(locator).to_have_count(0)
