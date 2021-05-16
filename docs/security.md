# Security

Allowing people to execute their own SQL directly against your database is risky business!

The safest way to use this tool is to create a read-only replica of your PostgreSQL database with a read-only role that enforces a statement time-limit for executed queries. Different database providers have different mechanisms for doing this - consult your hosting provider's documentation.

You should only provide access to this tool to people you trust. Malicious users may be able to negatively affect the performance of your servers through constructing SQL queries that deliberately consume large amounts of resources.

Configured correctly, Django SQL Dashboard uses a number of measures to keep your data and your database server safe:

- I strongly recommend creating a dedicated PostgreSQL role for accessing your database with read-only permissions granted to an allow-list of tables. PostgreSQL has extremely robust, well tested permissions which this tool can take full advantage of.
- Likewise, configuring a PostgreSQL-enforced query time limit can reduce the risk of expensive queries affecting the performance of the rest of your site.
- Setting up a read-only reporting replica for use with this tool can provide even stronger isolation from other site traffic.
- Your allow-list of tables should not include tables with sensitive information. Django's auth_user table contains password hashes, and the django_session table contains user session information. Neither should be exposed using this tool.
- Access to the dashboard is controlled by Django's permissions system, which means you can limit access to trusted team members.
- SQL queries can be passed to the dashboard using a ?sql= query string parameter - but this parameter needs to be signed before it will be executed. This should prevent attempts to trick you into executing malevolent SQL queries by sending you crafted links - while still allowing your team to create links to queries that can be securely shared.
- Any time a user views a dashboard page while logged in, `Cache-Control: private` is set on the response to ensure the authenticated dashboard will not be stored in any intermediary HTTP caches
