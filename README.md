# django-sql-dashboard

[![PyPI](https://img.shields.io/pypi/v/django-sql-dashboard.svg)](https://pypi.org/project/django-sql-dashboard/)
[![Changelog](https://img.shields.io/github/v/release/simonw/django-sql-dashboard?include_prereleases&label=changelog)](https://github.com/simonw/django-sql-dashboard/releases)
[![Tests](https://github.com/simonw/django-sql-dashboard/workflows/Test/badge.svg)](https://github.com/simonw/django-sql-dashboard/actions?query=workflow%3ATest)
[![Documentation Status](https://readthedocs.org/projects/django-sql-dashboard/badge/?version=latest)](http://django-sql-dashboard.datasette.io/en/latest/?badge=latest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/simonw/django-sql-dashboard/blob/main/LICENSE)

Django SQL Dashboard provides an authenticated interface for executing read-only SQL queries directly against your PostgreSQL database, bringing a useful subset of [Datasette](https://datasette.io/) to Django.

Applications include ad-hoc analysis and debugging, plus the creation of reporting dashboards that can be shared with team members or published online.

See my blog for [more about this project](https://simonwillison.net/2021/May/10/django-sql-dashboard/), including [a video demo](https://www.youtube.com/watch?v=ausrmMZkPEY).

Features include:

- Safely run read-only one or more SQL queries against your database and view the results in your browser
- Bookmark queries and share those links with other members of your team
- Create [saved dashboards](https://django-sql-dashboard.datasette.io/en/latest/saved-dashboards.html) from your queries, with full control over who can view and edit them
- [Named parameters](https://django-sql-dashboard.datasette.io/en/latest/sql.html#sql-parameters) such as `select * from entries where id = %(id)s` will be turned into form fields, allowing quick creation of interactive dashboards
- Produce [bar charts](https://django-sql-dashboard.datasette.io/en/latest/widgets.html#bar-label-bar-quantity), [progress bars](https://django-sql-dashboard.datasette.io/en/latest/widgets.html#total-count-completed-count) and more from SQL queries, with the ability to easily create new [custom dashboard widgets](https://django-sql-dashboard.datasette.io/en/latest/widgets.html#custom-widgets) using the Django template system
- Write SQL queries that safely construct and render [markdown](https://django-sql-dashboard.datasette.io/en/latest/widgets.html#markdown) and [HTML](https://django-sql-dashboard.datasette.io/en/latest/widgets.html#html)
- Export the full results of a SQL query as a downloadable CSV or TSV file, using a combination of Django's [streaming HTTP response](https://docs.djangoproject.com/en/3.2/ref/request-response/#django.http.StreamingHttpResponse) mechanism and PostgreSQL [server-side cursors](https://www.psycopg.org/docs/usage.html#server-side-cursors) to efficiently stream large amounts of data without running out of resources
- Copy and paste the results of SQL queries directly into tools such as Google Sheets or Excel
- Uses Django's authentication system, so dashboard accounts can be granted using Django's Admin tools

## Documentation

Full documentation is at [django-sql-dashboard.datasette.io](https://django-sql-dashboard.datasette.io/)

## Screenshot

<img width="1018" alt="Screenshot showing a SQL query that produces a table and one that produces a bar chart" src="https://user-images.githubusercontent.com/9599/124050883-42ad2300-d9d0-11eb-83e6-44ad85f7ef64.png">

## Alternatives

- [django-sql-explorer](https://github.com/groveco/django-sql-explorer) provides a related set of functionality that also works against database backends other than PostgreSQL
