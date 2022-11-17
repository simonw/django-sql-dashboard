# Installation and configuration

## Install using pip

Install this library using `pip`:

    $ pip install django-sql-dashboard

### Run migrations

The migrations create tables that store dashboards and queries:

    $ ./manage.py migrate

## Configuration

Add `"django_sql_dashboard"` to your `INSTALLED_APPS` in `settings.py`.

Add the following to your `urls.py`:

```python
from django.urls import path, include
import django_sql_dashboard

urlpatterns = [
    # ...
    path("dashboard/", include(django_sql_dashboard.urls)),
]
```

## Setting up read-only PostgreSQL credentials

The safest way to use this tool is against a dedicated read-only replica of your database - see [security](./security) for more details.

Create a new PostgreSQL user or role that is limited to read-only SELECT access to a specific list of tables.

If your read-only role is called `my-read-only-role`, you can grant access using the following SQL (executed as a privileged user):

```sql
GRANT USAGE ON SCHEMA PUBLIC TO "my-read-only-role";
```
This grants that role the ability to see what tables exist. You then need to grant `SELECT` access to specific tables like this:
```sql
GRANT SELECT ON TABLE
    public.locations_location,
    public.locations_county,
    public.django_content_type,
    public.django_migrations
TO "my-read-only-role";
```
Think carefully about which tables you expose to the dashboard - in particular, you should avoid exposing tables that contain sensitive data such as `auth_user` or `django_session`.

If you do want to expose `auth_user` - which can be useful if you want to join other tables against it to see details of the user that created another record - you can grant access to specific columns like so:
```sql
GRANT SELECT(
  id, last_login, is_superuser, username, first_name,
  last_name, email, is_staff, is_active, date_joined
) ON auth_user TO "my-read-only-role";
```
This will allow queries against everything except for the `password` column.

Note that if you use this pattern the query `select * from auth_user` will return a "permission denied" error. You will need to explicitly list the columns you would like to see from that table instead, for example `select id, username, date_joined from auth_user`.

## Configuring the "dashboard" database alias

Django SQL Dashboard defaults to executing all queries using the `"dashboard"` Django database alias.

You can define this `"dashboard"` database alias in `settings.py`. Your `DATABASES` section should look something like this:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "mydb",
        "USER": "read_write_user",
        "PASSWORD": "read_write_password",
        "HOST": "dbhost.example.com",
        "PORT": "5432",
    },
    "dashboard": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "mydb",
        "USER": "read_only_user",
        "PASSWORD": "read_only_password",
        "HOST": "dbhost.example.com",
        "PORT": "5432",
        "OPTIONS": {
            "options": "-c default_transaction_read_only=on -c statement_timeout=100"
        },
    },
}
```
In addition to the read-only user and password, pay attention to the `"OPTIONS"` section: this sets a statement timeout of 100ms - queries that take longer than that will be terminated with an error message. It also sets it so transactions will be read-only by default, as an extra layer of protection should your read-only user have more permissions that you intended.

Now visit `/dashboard/` as a staff user to start trying out the dashboard.

### Danger mode: configuration without a read-only database user

Some hosting environments such as Heroku charge extra for the ability to create read-only database users. For smaller projects with dashboard access only made available to trusted users it's possible to configure this tool without a read-only account, using the following options:

```python
    # ...
    "dashboard": {
        "ENGINE": "django.db.backends.postgresql",
        "USER": "read_write_user",
        # ...
        "OPTIONS": {
            "options": "-c default_transaction_read_only=on -c statement_timeout=100"
        },
    },
```
The `-c default_transaction_read_only=on` option here should prevent accidental writes from being executed, but note that dashboard users in this configuration will be able to access _all tables_ including tables that might contain sensitive information. Only use this trick if you are confident you fully understand the implications!

### dj-database-url and django-configurations

If you are using [dj-database-url](https://github.com/jacobian/dj-database-url) or [django-configurations](https://github.com/jazzband/django-configurations) _(with `database` extra requirement)_, your `DATABASES` section should look something like this:

```python
import dj_database_url

# ...

DATABASES = {
    "default": dj_database_url.config(env="DATABASE_URL"),
    "dashboard": dj_database_url.config(env="DATABASE_DASHBOARD_URL"),
}
```

You can define the two database url variables in your environment like this:

```ini
DATABASE_URL=postgresql://read_write_user:read_write_password@dbhost.example.com:5432/mydb
DATABASE_DASHBOARD_URL=postgresql://read_write_user:read_write_password@dbhost.example.com:5432/mydb?options=-c%20default_transaction_read_only%3Don%20-c%20statement_timeout%3D100
```

## Django permissions

Access to the `/dashboard/` interface is controlled by the Django permissions system. To grant a Django user or group access, grant them the `django_sql_dashboard.execute_sql` permission. This is displayed in the admin interface as:

    django_sql_dashboard | dashboard | Can execute arbitrary SQL queries

Dashboard editing is currently handled by the Django admin interface. This means a user needs to have **staff** status (allowing them access to the Django admin interface) in order to edit one of their saved dashboards.

The regular Django permission for "can edit dashboard" is ignored. Instead, a permission system that is specific to Django SQL Dashboard is used to control edit permissions. See {ref}`edit_permissions` for details.

## Additional settings

You can customize the following settings in Django's `settings.py` module:

- `DASHBOARD_DB_ALIAS = "db_alias"` - which database alias to use for executing these queries. Defaults to `"dashboard"`.
- `DASHBOARD_ROW_LIMIT = 1000` - the maximum number of rows that can be returned from a query. This defaults to 100.
- `DASHBOARD_UPGRADE_OLD_BASE64_LINKS` - prior to version 0.8a0 SQL URLs used base64-encoded JSON. If you set this to `True` any hits that include those old URLs will be automatically redirected to the upgraded new version. Use this if you have an existing installation of `django-sql-dashboard` that people already have saved bookmarks for.
- `DASHBOARD_ENABLE_FULL_EXPORT` - set this to `True` to enable the full results CSV/TSV export feature. It defaults to `False`. Enable this feature only if you are confident that the database alias you are using does not have write permissions to anything.

## Custom templates

The templates used by `django-sql-dashboard` extend a base template called `django_sql_dashboard/base.html`, which provides Django template blocks named `title` and `content`. You can customize the appearance of your dashboard installation by providing your own version of this base template in your own configured `templates/` directory.
