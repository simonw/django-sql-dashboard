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
