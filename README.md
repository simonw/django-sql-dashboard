# django-sql-dashboard

[![PyPI](https://img.shields.io/pypi/v/django-sql-dashboard.svg)](https://pypi.org/project/django-sql-dashboard/)
[![Changelog](https://img.shields.io/github/v/release/simonw/django-sql-dashboard?label=changelog&include_prereleases)](https://github.com/simonw/django-sql-dashboard/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/simonw/django-sql-dashboard/blob/main/LICENSE)

Django app for building dashboards using raw SQL queries

Brings a useful subset of [Datasette](https://datasette.io/) to Django.

Currently only works with PostgreSQL.

This is **very early alpha**. You should not yet trust this code, especially with regards to security. Do not run this in production (yet)!

## Screenshot

![Django_SQL_Dashboard screenshot](https://user-images.githubusercontent.com/9599/111020900-da352a00-837d-11eb-8991-73ec6e6608ef.png)

## Installation

Install this library using `pip`:

    $ pip install django-sql-dashboard

## Usage

Add `"django_sql_dashboard"` to your `INSTALLED_APPS`.

Add the following to your `urls.py`:

```python
from django.urls import path
from django_sql_dashboard.views import dashboard, dashboard_index

urlpatterns = [
    path("dashboard/", dashboard_index, name="django_sql_dashboard-index"),
    path("dashboard/<slug>/", dashboard),
    # ...
]
```

Now visit `/dashboard` as a staff user to start trying out the dashboard.

### SQL parameters

If your SQL query contains `%(name)s` parameters, `django-sql-dashboard` will convert those into form fields on the page and allow users to submit values for them. These will be correctly quoted and escaped in the SQL query.

Given the following SQL query:

```
select * from blog_entry where slug = %(slug)s
```
A form field called `slug` will be displayed, and the user will be able to use that to search for blog entries with that given slug.

Here's a more advanced example:

```sql
select * from location
where state_id = cast(%(state_id)s as integer)
and name ilike '%%' || %(search)s || '%%';
```
Here a form will be displayed with `state_id` and `search` fields.

The values provided by the user will always be treated like strings - so in this example the `state_id` is cast to integer in order to be matched with an integer column.

Any `%` characters - for example in the `ilike` query above - need to be escaped by providing them twice: `%%`.

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
