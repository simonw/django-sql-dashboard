# django-sql-dashboard

[![PyPI](https://img.shields.io/pypi/v/django-sql-dashboard.svg)](https://pypi.org/project/django-sql-dashboard/)
[![Changelog](https://img.shields.io/github/v/release/simonw/django-sql-dashboard?label=changelog&include_prereleases)](https://github.com/simonw/django-sql-dashboard/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/simonw/django-sql-dashboard/blob/main/LICENSE)

Django app for building dashboards using raw SQL queries

Brings a useful subset of [Datasette](https://datasette.io/) to Django.

Currently only works with PostgreSQL.

This is **very early alpha**. You should not yet trust this code, especially with regards to security. Do not run this in production (yet)!

<!-- toc -->

- [Screenshot](#screenshot)
- [Installation](#installation)
- [Usage](#usage)
  * [SQL parameters](#sql-parameters)
  * [Widgets](#widgets)
    + [bar_label, bar_quantity](#bar_label-bar_quantity)
    + [big_number, label](#big_number-label)
    + [markdown](#markdown)
    + [html](#html)
  * [Custom widgets](#custom-widgets)
- [Development](#development)

<!-- tocstop -->

## Screenshot

![Django_SQL_Dashboard screenshot](https://user-images.githubusercontent.com/9599/111020900-da352a00-837d-11eb-8991-73ec6e6608ef.png)

## Installation

Install this library using `pip`:

    $ pip install django-sql-dashboard

## Usage

Add `"django_sql_dashboard"` to your `INSTALLED_APPS` in `settings.py`.

Define a `"dashboard"` database alias in `settings.py`. It should look something like this:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "mydb",
    },
    "dashboard": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "mydb",
        "OPTIONS": {"options": "-c default_transaction_read_only=on -c statement_timeout=100"},
    },
}
```
Even better: create a new PostgreSQL role that is limited to read-only SELECT access to a list of tables, following [these instructions](https://til.simonwillison.net/postgresql/read-only-postgresql-user).

Add the following to your `urls.py`:

```python
from django.urls import path, inclued
import django_sql_dashboard

urlpatterns = [
    # ...
    path("dashboard/", include(django_sql_dashboard.urls)),
]
```

Now visit `/dashboard/` as a staff user to start trying out the dashboard.

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

### Widgets

SQL queries default to displaying as a table. Other forms of display - called widgets - are also available, and are selected based on the names of the columns returned by the query.

#### bar_label, bar_quantity

A query that returns columns called `bar_label` and `bar_quantity` will be rendered as a simple bar chart, using [Vega-Lite](https://vega.github.io/vega-lite/).

For example:

```sql
select
  county.name as bar_label,
  count(*) as bar_quantity
from location
  join county on county.id = location.county_id
group by county.name
order by count(*) desc limit 10
```

Or using a static list of values:

```sql
SELECT * FROM (
    VALUES (1, 'one'), (2, 'two'), (3, 'three')
) AS t (bar_quantity, bar_label);
```

#### big_number, label

If you want to display the results as a big number accompanied by a label, you can do so by returning `big_number` and `label` columns from your query, for example.

```sql
select 'Number of states' as label, count(*) as big_number from states;
```

#### markdown

Return a single column called `markdown` to render the contents as Markdown, for example:

```sql
select '# Number of states: ' || count(*) as markdown from states;
```

#### html

Return a single column called `html` to render the contents directly as HTML. This HTML is filtered using [Bleach](https://github.com/mozilla/bleach) so the only tags allowed are `a[href]`, `abbr`, `acronym`, `b`, `blockquote`, `code`, `em`, `i`, `li`, `ol`, `strong`, `ul`, `pre`, `p`, `h1`, `h2`, `h3`, `h4`, `h5`, `h6`.

```sql
select '<h1>Number of states: ' || count(*) || '</h1> as markdown from states;
```

### Custom widgets

You can define your own custom widgets by creating templates with special names.

Decide on the column names that you wish to customize for, then sort them alphabetically and join them with hyphens to create your template name.

For example, you could define a widget that handles results returned as `placename`, `geojson` by creating a template called `geojson-label.html`.

Save that in one of your template directories as `django_sql_dashboard/widgets/geojson-label.html`.

Any SQL query that returns exactly the columns `placename` and `geojson` will now be rendered by your custom template file.

Within your custom template you will have access to a template variable called `result` with the following keys:

- `result.sql` - the SQL query that is being displayed
- `rows` - a list of rows, where each row is a dictionary mapping columns to their values
- `row_lists` - a list of rows, where each row is a list of the values in that row
- `description` - the psycopg2 cursor description
- `truncated` - boolean, specifying whether the results were truncated (at 100 items) or not
- `duration_ms` - how long the query took, in floating point milliseconds
- `templates` - a list of templates that were considered for rendering this widget

You can find examples of widget templates in the [templates/django_sql_dashboard/widgets](https://github.com/simonw/django-sql-dashboard/tree/main/django_sql_dashboard/templates/django_sql_dashboard/widgets) directory.

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
