# Saved dashboards

A set of SQL queries can be used to create a saved dashboard. Saved dashboards have URLs and support permissions, so you can specify which users are allowed to see which dashboard.

Saved dashboards currently need to be created using the Django Admin interface.

Available view permissions are as follows:

- `private`: Only the user who created (owns) the dashboard can view
- `public`: Any user can view
- `unlisted`: Any user can view, but they need to know the URL (this feature is not complete)
- `loggedin`: Any logged-in user can view
- `group`: Any user who is a member of the `view_group` attached to the dashboard can view
- `staff`: Any user who is staff can view
- `superuser`: Any user who is a superuser can view

Edit permissions exist in the admin interface but do not yet do anything. Follow [#27](https://github.com/simonw/django-sql-dashboard/issues/27) for progress on this.
