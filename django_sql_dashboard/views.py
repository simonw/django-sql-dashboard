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
from .utils import SQL_SALT, displayable_rows, extract_named_parameters

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
        signed_sqls = [
            signing.dumps(query, salt=SQL_SALT) for query in sqls if query.strip()
        ]
        params = {
            "sql": signed_sqls,
        }
        params.update(other_pairs)
        return HttpResponseRedirect(request.path + "?" + urlencode(params, doseq=True))
    sql_queries = []
    for signed_sql in request.GET.getlist("sql"):
        try:
            sql_queries.append(signing.loads(signed_sql, salt=SQL_SALT))
        except ValueError:
            pass
    return _dashboard_index(request, sql_queries, title="Django SQL Dashboard")


def _dashboard_index(
    request, sql_queries, title=None, description=None, saved_dashboard=False
):
    query_results = []
    alias = getattr(settings, "DASHBOARD_DB_ALIAS", "dashboard")
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
    for sql in sql_queries:
        for p in extract_named_parameters(sql):
            if p not in parameters:
                parameters.append(p)
    parameter_values = {
        parameter: request.GET.get(parameter, "")
        for parameter in parameters
        if parameter != "sql"
    }
    extra_qs = "&{}".format(urlencode(parameter_values)) if parameter_values else ""
    results_index = -1
    if sql_queries:
        for sql in sql_queries:
            results_index += 1
            sql = sql.strip()
            if ";" in sql.rstrip(";"):
                query_results.append(
                    {
                        "index": str(results_index),
                        "sql": sql,
                        "rows": [],
                        "row_lists": [],
                        "description": [],
                        "columns": [],
                        "truncated": False,
                        "extra_qs": extra_qs,
                        "error": "';' not allowed in SQL queries",
                        "templates": ERROR_TEMPLATES,
                    }
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
                        rows = list(cursor.fetchmany(101))
                    except ProgrammingError as e:
                        rows = [{"statusmessage": str(cursor.statusmessage)}]
                    duration_ms = (time.perf_counter() - start) * 1000.0
                except Exception as e:
                    query_results.append(
                        {
                            "index": str(results_index),
                            "sql": sql,
                            "rows": [],
                            "row_lists": [],
                            "description": [],
                            "columns": [],
                            "truncated": False,
                            "extra_qs": extra_qs,
                            "error": str(e),
                            "templates": ERROR_TEMPLATES,
                        }
                    )
                else:
                    templates = ["django_sql_dashboard/widgets/default.html"]
                    columns = [c.name for c in cursor.description]
                    template_name = ("-".join(sorted(columns))) + ".html"
                    if len(template_name) < 255:
                        templates.insert(
                            0,
                            "django_sql_dashboard/widgets/" + template_name,
                        )
                    display_rows = displayable_rows(rows[:100], columns)
                    query_results.append(
                        {
                            "index": str(results_index),
                            "sql": sql,
                            "rows": display_rows,
                            "row_lists": [
                                [row[column] for column in columns]
                                for row in display_rows
                            ],
                            "description": cursor.description,
                            "columns": columns,
                            "truncated": len(rows) == 101,
                            "extra_qs": extra_qs,
                            "duration_ms": duration_ms,
                            "templates": templates,
                        }
                    )
                finally:
                    cursor.execute("ROLLBACK;")
    return render(
        request,
        "django_sql_dashboard/dashboard.html",
        {
            "query_results": query_results,
            "available_tables": available_tables,
            "title": title,
            "description": description,
            "saved_dashboard": saved_dashboard,
            "user_can_execute_sql": request.user.has_perm(
                "django_sql_dashboard.execute_sql"
            ),
            "parameter_values": parameter_values.items(),
        },
    )


def dashboard(request, slug):
    dashboard = get_object_or_404(Dashboard, slug=slug)
    # Can current user see it, based on view_policy?
    view_policy = dashboard.view_policy
    owner = dashboard.owned_by
    denied = HttpResponseForbidden("You cannot access this dashboard")
    if view_policy == Dashboard.ViewPolicies.PRIVATE:
        if request.user != owner:
            return denied
    elif view_policy == Dashboard.ViewPolicies.PUBLIC:
        pass
    elif view_policy == Dashboard.ViewPolicies.UNLISTED:
        pass
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
    )
