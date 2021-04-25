# Installation and configuration

## Install using pip

Install this library using `pip`:

    $ pip install django-sql-dashboard

## Configuration

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

## Additional settings

You can customize the following settings in Django's `settings.py` module:

- `DASHBOARD_DB_ALIAS = "db_alias"` - which database alias to use for executing these queries. Defaults to `"dashboard"`.
- `DASHBOARD_ROW_LIMIT = 1000` - the maximum number of rows that can be returned from a query. This defaults to 100.
- `DASHBOARD_UPGRADE_OLD_BASE64_LINKS` - prior to version 0.8a0 SQL URLs used base64-encoded JSON. If you set this to `True` any hits that include those old URLs will be automatically redirected to the upgraded new version. Use this if you have an existing installation of `django-sql-dashboard` that people already have saved bookmarks for.
- `DASHBOARD_ENABLE_FULL_EXPORT` - set this to `True` to enable the full results CSV/TSV export feature. It defaults to `False`. Enable this feature only if you are confident that the database alias you are using does not have write permissions to anything.

## Custom templates

The templates used by `django-sql-dashboard` extend a base template called `django_sql_dashboard/base.html`, which provides Django template blocks named `title` and `content`. You can customize the appearance of your dashboard installation by providing your own version of this base template in your own configured `templates/` directory.
