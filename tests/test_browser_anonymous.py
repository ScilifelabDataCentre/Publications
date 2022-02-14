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
    return utils.get_settings(BASE_URL="http://localhost:8885")


def test_about(settings, page):  # 'page' fixture from 'pytest-playwright'
    "Test access to 'About' pages."
    page.set_default_navigation_timeout(3000)

    page.goto(settings["BASE_URL"])
    page.click("text=About")
    page.click("text=Overview")
    assert page.url == f"{settings['BASE_URL']}/docs/overview"

    page.goto(settings["BASE_URL"])
    page.click("text=About")
    page.click("text=Contact")
    assert page.url == f"{settings['BASE_URL']}/contact"

    page.goto(settings["BASE_URL"])
    page.click("text=About")
    page.click("text=Overview")
    assert page.url == f"{settings['BASE_URL']}/docs/overview"

    # page.wait_for_timeout(3000)
