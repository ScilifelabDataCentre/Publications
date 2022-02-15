"""Test browser anonymous access.

After installing from PyPi using the 'requirements.txt' file, one must do:
$ playwright install

To run while displaying browser window:
$ pytest --headed

Much of the code below was created using the playwright code generation feature:
$ playwright codegen http://localhost:5001/
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
