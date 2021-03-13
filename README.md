# django-sql-dashboard

[![PyPI](https://img.shields.io/pypi/v/django-sql-dashboard.svg)](https://pypi.org/project/django-sql-dashboard/)
[![Changelog](https://img.shields.io/github/v/release/simonw/django-sql-dashboard?label=changelog)](https://github.com/simonw/django-sql-dashboard/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/simonw/django-sql-dashboard/blob/main/LICENSE)

Django app for building dashboards using raw SQL queries

Brings a useful subset of [Datasette](https://datasette.io/) to Django.

Currently only works with PostgreSQL.

This is **very early alpha**. You should not yet trust this code, especially with regards to security. Do not run this in production (yet)!

## Installation

Install this library using `pip`:

    $ pip install django-sql-dashboard

## Usage

Add `"django_sql_dashboard"` to your `INSTALLED_APPS`.

Add the following to your `urls.py`:

```python
from django.urls import path
from django_sql_dashboard.views import dashboard

urlpatterns = [
    path("dashboard", dashboard),
    # ...
]
```

Now visit `/dashboard` as a staff user to start trying out the dashboard.

## Development

To contribute to this library, first checkout the code. Then create a new virtual environment:

    cd django-sql-dashboard
    python -mvenv venv
    source venv/bin/activate

Or if you are using `pipenv`:

    pipenv shell

Now install the dependencies and tests:

    pip install -e '.[test]'

To run the tests:

    pytest
