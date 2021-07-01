# Saved dashboards

A set of SQL queries can be used to create a saved dashboard. Saved dashboards have URLs and support permissions, so you can specify which users are allowed to see which dashboard.

You can create a saved dashboard from the interactive dashboard interface (at `/dashboard/`) - execute some queries, then scroll down to the "Save this dashboard" form.

## View permissions

The following viewing permission policies are available:

- `private`: Only the user who created (owns) the dashboard can view
- `public`: Any user can view
- `unlisted`: Any user can view, but they need to know the URL (this feature is not complete)
- `loggedin`: Any logged-in user can view
- `group`: Any user who is a member of the `view_group` attached to the dashboard can view
- `staff`: Any user who is staff can view
- `superuser`: Any user who is a superuser can view

(edit_permissions)=

## Edit permissions

The edit policy controls which users are allowed to edit a dashboard - defaulting to the user who created that dashboard.

Editing currently takes place through the Django Admin - so only users who are staff members with access to that interface will be able to edit their dashboards.

The full list of edit policy options are:

- `private`: Only the user who created (owns) the dashboard can edit
- `loggedin`: Any logged-in user can edit
- `group`: Any user who is a member of the `edit_group` attached to the dashboard can edit
- `staff`: Any user who is staff can edit
- `superuser`: Any user who is a superuser can edit

Dashboards belong to the user who created them. Only Django super-users can re-assign ownership of dashboards to other users.
