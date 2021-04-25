import time
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.core import signing
from django.db import connections
from django.db.utils import ProgrammingError
from django.http.response import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render

from .models import Dashboard
from .utils import (
    check_for_base64_upgrade,
    displayable_rows,
    extract_named_parameters,
    sign_sql,
    unsign_sql,
)

ERROR_TEMPLATES = [
    "django_sql_dashboard/widgets/error.html",
    "django_sql_dashboard/widgets/default.html",
]


@permission_required("django_sql_dashboard.execute_sql")
def dashboard_index(request):
    if request.method == "POST":
        # Convert ?sql= into signed values and redirect as GET
        sqls = request.POST.getlist("sql")
        other_pairs = [
            (key, value)
            for key, value in request.POST.items()
            if key not in ("sql", "csrfmiddlewaretoken")
        ]
        signed_sqls = [sign_sql(sql) for sql in sqls if sql.strip()]
        params = {
            "sql": signed_sqls,
        }
        params.update(other_pairs)
        return HttpResponseRedirect(request.path + "?" + urlencode(params, doseq=True))
    sql_queries = []
    unverified_sql_queries = []
    for signed_sql in request.GET.getlist("sql"):
        sql, signature_verified = unsign_sql(signed_sql)
        if signature_verified:
            sql_queries.append(sql)
        else:
            unverified_sql_queries.append(sql)
    if getattr(settings, "DASHBOARD_UPGRADE_OLD_BASE64_LINKS", None):
        redirect_querystring = check_for_base64_upgrade(sql_queries)
        if redirect_querystring:
            return HttpResponseRedirect(request.path + redirect_querystring)
    return _dashboard_index(
        request,
        sql_queries,
        unverified_sql_queries=unverified_sql_queries,
    )


def _dashboard_index(
    request,
    sql_queries,
    unverified_sql_queries=None,
    title=None,
    description=None,
    saved_dashboard=False,
    cache_control_private=False,
):
    query_results = []
    alias = getattr(settings, "DASHBOARD_DB_ALIAS", "dashboard")
    row_limit = getattr(settings, "DASHBOARD_ROW_LIMIT", None) or 100
    connection = connections[alias]
    with connection.cursor() as tables_cursor:
        tables_cursor.execute(
            """
            SELECT table_name
            FROM   information_schema.table_privileges 
            WHERE  grantee = current_user and privilege_type = 'SELECT'
            ORDER BY table_name
        """
        )
        available_tables = [t[0] for t in tables_cursor.fetchall()]

    parameters = []
    sql_query_parameter_errors = []
    for sql in sql_queries:
        try:
            extracted = extract_named_parameters(sql)
            for p in extracted:
                if p not in parameters:
                    parameters.append(p)
            sql_query_parameter_errors.append(False)
        except ValueError as e:
            if "%" in sql:
                sql_query_parameter_errors.append(
                    r"Invalid query - try escaping single '%' as double '%%'"
                )
            else:
                sql_query_parameter_errors.append(str(e))
    parameter_values = {
        parameter: request.GET.get(parameter, "")
        for parameter in parameters
        if parameter != "sql"
    }
    extra_qs = "&{}".format(urlencode(parameter_values)) if parameter_values else ""
    results_index = -1
    if sql_queries:
        for sql, parameter_error in zip(sql_queries, sql_query_parameter_errors):
            results_index += 1
            sql = sql.strip().rstrip(";")
            base_error_result = {
                "index": str(results_index),
                "sql": sql,
                "textarea_rows": min(5, len(sql.split("\n"))),
                "rows": [],
                "row_lists": [],
                "description": [],
                "columns": [],
                "column_details": [],
                "truncated": False,
                "extra_qs": extra_qs,
                "error": None,
                "templates": ERROR_TEMPLATES,
            }
            if parameter_error:
                query_results.append(
                    dict(
                        base_error_result,
                        error=parameter_error,
                    )
                )
                continue
            if ";" in sql:
                query_results.append(
                    dict(base_error_result, error="';' not allowed in SQL queries")
                )
                continue
            with connection.cursor() as cursor:
                duration_ms = None
                try:
                    cursor.execute("BEGIN;")
                    start = time.perf_counter()
                    # Running a SELECT prevents future SET TRANSACTION READ WRITE:
                    cursor.execute("SELECT 1;", parameter_values)
                    cursor.fetchall()
                    cursor.execute(sql, parameter_values)
                    try:
                        rows = list(cursor.fetchmany(row_limit + 1))
                    except ProgrammingError as e:
                        rows = [{"statusmessage": str(cursor.statusmessage)}]
                    duration_ms = (time.perf_counter() - start) * 1000.0
                except Exception as e:
                    query_results.append(dict(base_error_result, error=str(e)))
                else:
                    templates = ["django_sql_dashboard/widgets/default.html"]
                    columns = [c.name for c in cursor.description]
                    template_name = ("-".join(sorted(columns))) + ".html"
                    if len(template_name) < 255:
                        templates.insert(
                            0,
                            "django_sql_dashboard/widgets/" + template_name,
                        )
                    display_rows = displayable_rows(rows[:row_limit])
                    column_details = [
                        {"name": column, "is_unambiguous": columns.count(column) == 1}
                        for column in columns
                    ]
                    query_results.append(
                        {
                            "index": str(results_index),
                            "sql": sql,
                            "textarea_rows": len(sql.split("\n")),
                            "rows": [dict(zip(columns, row)) for row in display_rows],
                            "row_lists": display_rows,
                            "description": cursor.description,
                            "columns": columns,
                            "column_details": column_details,
                            "truncated": len(rows) == row_limit + 1,
                            "extra_qs": extra_qs,
                            "duration_ms": duration_ms,
                            "templates": templates,
                        }
                    )
                finally:
                    cursor.execute("ROLLBACK;")
    # Page title, composed of truncated SQL queries
    html_title = "SQL Dashboard"
    if sql_queries:
        html_title = "SQL: " + " [,] ".join(sql_queries)
    response = render(
        request,
        "django_sql_dashboard/dashboard.html",
        {
            "title": title or "SQL Dashboard",
            "html_title": title or html_title,
            "query_results": query_results,
            "unverified_sql_queries": unverified_sql_queries,
            "available_tables": available_tables,
            "description": description,
            "saved_dashboard": saved_dashboard,
            "user_can_execute_sql": request.user.has_perm(
                "django_sql_dashboard.execute_sql"
            ),
            "parameter_values": parameter_values.items(),
        },
    )
    if cache_control_private:
        response["cache-control"] = "private"
    response["Content-Security-Policy"] = "frame-ancestors 'self'"
    return response


def dashboard(request, slug):
    dashboard = get_object_or_404(Dashboard, slug=slug)
    # Can current user see it, based on view_policy?
    view_policy = dashboard.view_policy
    owner = dashboard.owned_by
    denied = HttpResponseForbidden("You cannot access this dashboard")
    denied["cache-control"] = "private"
    cache_control_private = True
    if view_policy == Dashboard.ViewPolicies.PRIVATE:
        if request.user != owner:
            return denied
    elif view_policy == Dashboard.ViewPolicies.PUBLIC:
        cache_control_private = False
    elif view_policy == Dashboard.ViewPolicies.UNLISTED:
        cache_control_private = False
    elif view_policy == Dashboard.ViewPolicies.LOGGEDIN:
        if not request.user.is_authenticated:
            return denied
    elif view_policy == Dashboard.ViewPolicies.GROUP:
        if (not request.user.is_authenticated) or not (
            request.user == owner
            or request.user.groups.filter(pk=dashboard.view_group_id).exists()
        ):
            return denied
    elif view_policy == Dashboard.ViewPolicies.STAFF:
        if (not request.user.is_authenticated) or (
            request.user != owner and not request.user.is_staff
        ):
            return denied
    elif view_policy == Dashboard.ViewPolicies.SUPERUSER:
        if (not request.user.is_authenticated) or (
            request.user != owner and not request.user.is_superuser
        ):
            return denied
    return _dashboard_index(
        request,
        sql_queries=[query.sql for query in dashboard.queries.all()],
        title=dashboard.title,
        description=dashboard.description,
        saved_dashboard=True,
        cache_control_private=cache_control_private,
    )
