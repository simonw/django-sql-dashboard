# django-sql-dashboard

[![PyPI](https://img.shields.io/pypi/v/django-sql-dashboard.svg)](https://pypi.org/project/django-sql-dashboard/)
[![Changelog](https://img.shields.io/github/v/release/simonw/django-sql-dashboard?include_prereleases&label=changelog)](https://github.com/simonw/django-sql-dashboard/releases)
[![Tests](https://github.com/simonw/django-sql-dashboard/workflows/Test/badge.svg)](https://github.com/simonw/django-sql-dashboard/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/simonw/django-sql-dashboard/blob/main/LICENSE)

Django SQL Dashboard provides an authenticated interface for executing read-only SQL queries directly against your PostgreSQL database, bringing a useful subset of Datasette to Django.

Applications include ad-hoc analysis and debugging, plus the creation of reporting dashboards that can be shared with team members or published online.

Features include:

- Safely run read-only one or more SQL queries against your database and view the results in your browser
- Bookmark queries and share those links with other members of your team
- Create [saved dashboards](https://django-sql-dashboard.datasette.io/en/latest/saved-dashboards.html) from your queries, with full control over who can view and edit them
- [Named parameters](https://django-sql-dashboard.datasette.io/en/latest/sql.html#sql-parameters) such as `select * from entries where id = %(id)s` will be turned into form fields, allowing quick creation of interactive dashboards
- Produce [bar charts](https://django-sql-dashboard.datasette.io/en/latest/widgets.html#bar-label-bar-quantity), [progress bars](https://django-sql-dashboard.datasette.io/en/latest/widgets.html#total-count-completed-count) and more from SQL queries, with the ability to easily create new [custom dashboard widgets](https://django-sql-dashboard.datasette.io/en/latest/widgets.html#custom-widgets) using the Django template system
- Write SQL queries that safely construct and render [markdown](https://django-sql-dashboard.datasette.io/en/latest/widgets.html#markdown) and [HTML](https://django-sql-dashboard.datasette.io/en/latest/widgets.html#html)
- Export the full results of SQL queries as downloadable CSV or TSV files
- Copy and paste the results of SQL queries directly into tools such as Google Sheets or Excel
- Uses Django's authentication system, so dashboard accounts can be granted using Django's Admin tools

## Documentation

Full documentation is at [django-sql-dashboard.datasette.io](https://django-sql-dashboard.datasette.io/)

## Screenshot

<img width="1006" alt="Screenshot showing a SQL query that produces a table and one that produces a bar chart" src="https://user-images.githubusercontent.com/9599/116013366-b9026300-a5e4-11eb-85f5-3dd655acc949.png">
