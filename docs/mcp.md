# MCP server

Django SQL Dashboard includes a [Model Context Protocol](https://modelcontextprotocol.io/)
(MCP) server, so LLM-powered tools such as Claude can explore your database
and answer questions by executing read-only SQL queries.

The server is enabled automatically when you include `django_sql_dashboard.urls`
in your URL configuration. If the dashboard is mounted at `/dashboard/` the MCP
endpoint is:

    https://your-site.example.com/dashboard/-/mcp

The endpoint implements the stateless variant of the MCP Streamable HTTP
transport, using JSON responses. Configure an MCP client to connect to that
URL. Note that the URL has no trailing slash.

## Tools

Five read-only tools are exposed.

Three SQL tools, available to users with the
`django_sql_dashboard.execute_sql` permission:

- `list_tables` lists the tables that are visible to the dashboard's database
  connection.
- `get_schema` returns every table with its columns and their PostgreSQL
  types, so a model can construct correct queries.
- `execute_sql` executes a single read-only SQL query and returns its columns
  and rows. Queries can use `%(name)s` style parameters, with values passed
  in a separate `parameters` argument. Results are truncated to the
  `DASHBOARD_ROW_LIMIT` setting (default 100 rows) and a `truncated` flag
  indicates when this has happened.

And two [saved dashboard](saved-dashboards.md) tools, which follow each
dashboard's view policy rather than requiring the `execute_sql` permission:

- `list_dashboards` lists the dashboards the current user is allowed to
  view: their slug, title and description. Unlisted dashboards are not
  included, matching how they are hidden from the dashboard index page.
- `execute_dashboard` executes every query saved on a dashboard, identified
  by its slug, and returns the results of each query - or a per-query error
  message if one of them fails. Values for `%(name)s` parameters used by
  the dashboard's queries can be passed in the `parameters` argument.
  Unlisted dashboards can be executed by anyone who knows their slug.

Because the dashboard tools follow view policies, an anonymous MCP client
with no credentials at all can connect and use dashboards that have been
made public. `tools/list` only advertises the tools the current user is
allowed to use, so anonymous clients see just the two dashboard tools.

## Authentication and security

The MCP endpoint applies the same rules as the rest of the dashboard:

- The SQL tools require the request to be authenticated as a user with the
  `django_sql_dashboard.execute_sql` permission - calling them without it
  returns a tool error. MCP clients can authenticate in the same way
  as the user's browser, for example by passing a valid session cookie,
  or using a token - see below.
- The dashboard tools check the view policy of each dashboard, exactly like
  the dashboard pages themselves: a dashboard that is not visible to the
  current user is reported as not existing, whether it is missing or merely
  private.
- SQL executes against the `DASHBOARD_DB_ALIAS` database connection, inside
  a transaction that is always rolled back, using the same protective
  pattern as the dashboard itself.
- Queries containing `;` are rejected, so only one statement can run at a
  time.

As with the rest of Django SQL Dashboard, you should configure the dashboard
database connection to use a read-only PostgreSQL role with a statement
timeout - see [Security](security.md) for details. The MCP server deliberately
provides no way to run write queries, but the read-only database role is the
real enforcement mechanism.

## Token authentication

Headless MCP clients usually cannot log in through a browser to obtain a
session cookie. To support them, the optional `DASHBOARD_MCP_TOKENS` setting
maps secret tokens to usernames:

```python
DASHBOARD_MCP_TOKENS = {
    "your-secret-token": "username",
}
```

An MCP client can then authenticate by sending that token in an
`Authorization` header:

    Authorization: Bearer your-secret-token

A request with a valid token is treated as coming from the corresponding
user, who must still have the `django_sql_dashboard.execute_sql` permission
to use the SQL tools.
Tokens for missing or inactive users are rejected, and if a `Bearer` header
is present it must be valid - an invalid token is never ignored in favor of
the request's session cookie.

Treat these tokens like passwords: each one grants the full dashboard SQL
access of its user. Keep them out of source control (for example by loading
them from environment variables) and rotate them by changing the setting.
