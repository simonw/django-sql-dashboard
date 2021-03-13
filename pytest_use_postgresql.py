import os

import pytest
from dj_database_url import parse
from django.conf import settings
from testing.postgresql import Postgresql

_POSTGRESQL = Postgresql()


@pytest.hookimpl(tryfirst=True)
def pytest_load_initial_conftests(early_config, parser, args):
    os.environ["DJANGO_SETTINGS_MODULE"] = early_config.getini("DJANGO_SETTINGS_MODULE")
    settings.DATABASES["default"] = parse(_POSTGRESQL.url())


def pytest_unconfigure(config):
    _POSTGRESQL.stop()
