# Running SQL queries

Visit `/dashboard/` to get started. This interface allows you to execute one or more PostgreSQL SQL queries.

Results will be displayed below each query, limited to a maxmim of 100 rows.

The queries you have executed are encoded into the URL of the page. This means you can bookmark queries and share those links with other people who can access your dashboard.

Note that the queries in the URL are signed using Django's `SECRET_KEY` setting. This means that changing you secret will break your bookmarked URLs.

## SQL parameters

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