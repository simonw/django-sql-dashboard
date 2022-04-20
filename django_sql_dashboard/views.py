import csv
import hashlib
import re
import time
from io import StringIO
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import connections
from django.db.utils import ProgrammingError
from django.forms import CharField, ModelForm, Textarea
from django.http.response import (
    HttpResponseForbidden,
    HttpResponseRedirect,
    StreamingHttpResponse,
)
from django.shortcuts import get_object_or_404, render
from django.utils.safestring import mark_safe

from psycopg2.extensions import quote_ident

from .models import Dashboard
from .utils import (
    apply_sort,
    check_for_base64_upgrade,
    displayable_rows,
    extract_named_parameters,
    postgresql_reserved_words,
    sign_sql,
    unsign_sql,
)

# https://github.com/simonw/django-sql-dashboard/issues/58
MAX_REDIRECT_LENGTH = 1800


class SaveDashboardForm(ModelForm):
    slug = CharField(required=False, label="URL", help_text='For example "daily-stats"')

    class Meta:
        model = Dashboard
        fields = (
            "title",
            "slug",
            "description",
            "view_policy",
            "view_group",
            "edit_policy",
            "edit_group",
        )
        widgets = {
            "description": Textarea(
                attrs={
                    "placeholder": "Optional description, shown at the top of the dashboard page (Markdown allowed)"
                }
            )
        }


@login_required
def dashboard_index(request):
    if not request.user.has_perm("django_sql_dashboard.execute_sql"):
        return HttpResponseForbidden("You do not have permission to execute SQL")
    sql_queries = []
    too_long_so_use_post = False
    save_form = SaveDashboardForm(prefix="_save")
    if request.method == "POST":
        # Is this an export?
        if any(
            k for k in request.POST.keys() if k.startswith("export_")
        ) and request.user.has_perm("django_sql_dashboard.execute_sql"):
            if not getattr(settings, "DASHBOARD_ENABLE_FULL_EXPORT", None):
                return HttpResponseForbidden("The export feature is not enabled")
            return export_sql_results(request)
        sqls = [sql for sql in request.POST.getlist("sql") if sql.strip()]

        saving = False
        # How about a save?
        if request.POST.get("_save-slug"):
            save_form = SaveDashboardForm(request.POST, prefix="_save")
            saving = True
            if save_form.is_valid():
                dashboard = save_form.save(commit=False)
                dashboard.owned_by = request.user
                dashboard.save()
                for sql in sqls:
                    dashboard.queries.create(sql=sql)
                return HttpResponseRedirect(dashboard.get_absolute_url())

        # Convert ?sql= into signed values and redirect as GET
        other_pairs = [
            (key, value)
            for key, value in request.POST.items()
            if key not in ("sql", "csrfmiddlewaretoken")
            and not key.startswith("_save-")
        ]
        signed_sqls = [sign_sql(sql) for sql in sqls if sql.strip()]
        params = {
            "sql": signed_sqls,
        }
        params.update(other_pairs)
        redirect_path = request.path + "?" + urlencode(params, doseq=True)
        # Is this short enough for us to redirect?
        too_long_so_use_post = len(redirect_path) > MAX_REDIRECT_LENGTH
        if not saving and not too_long_so_use_post:
            return HttpResponseRedirect(redirect_path)
        else:
            sql_queries = sqls
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
        too_long_so_use_post=too_long_so_use_post,
        extra_context={"save_form": save_form},
    )


def _dashboard_index(
    request,
    sql_queries,
    unverified_sql_queries=None,
    title=None,
    description=None,
    dashboard=None,
    too_long_so_use_post=False,
    template="django_sql_dashboard/dashboard.html",
    extra_context=None,
):
    query_results = []
    alias = getattr(settings, "DASHBOARD_DB_ALIAS", "dashboard")
    row_limit = getattr(settings, "DASHBOARD_ROW_LIMIT", None) or 100
    connection = connections[alias]
    reserved_words = postgresql_reserved_words(connection)
    with connection.cursor() as tables_cursor:
        tables_cursor.execute(
            """
            with visible_tables as (
              select table_name
                from information_schema.tables
                where table_schema = 'public'
                order by table_name
            ),
            reserved_keywords as (
              select word
                from pg_get_keywords()
                where catcode = 'R'
            )
            select
              information_schema.columns.table_name,
              array_to_json(array_agg(cast(column_name as text) order by ordinal_position)) as columns
            from
              information_schema.columns
            join
              visible_tables on
              information_schema.columns.table_name = visible_tables.table_name
            where
              information_schema.columns.table_schema = 'public'
            group by
              information_schema.columns.table_name
            order by
              information_schema.columns.table_name
        """
        )
        fetched = tables_cursor.fetchall()
        available_tables = [
            {
                "name": row[0],
                "columns": ", ".join(row[1]),
                "sql_columns": ", ".join(
                    [
                        '"{}"'.format(column) if column in reserved_words else column
                        for column in row[1]
                    ]
                ),
            }
            for row in fetched
        ]

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
        parameter: request.POST.get(parameter, request.GET.get(parameter, ""))
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
                "templates": ["django_sql_dashboard/widgets/error.html"],
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
                    cursor.execute("SELECT 1;")
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
                        {
                            "name": column,
                            "is_unambiguous": columns.count(column) == 1,
                            "sort_sql": apply_sort(sql, column),
                            "sort_desc_sql": apply_sort(sql, column, True),
                        }
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

    if dashboard and dashboard.title:
        html_title = dashboard.title

    # Add named parameter values, if any exist
    provided_values = {
        key: value for key, value in parameter_values.items() if value.strip()
    }
    if provided_values:
        if len(provided_values) == 1:
            html_title += ": {}".format(list(provided_values.values())[0])
        else:
            html_title += ": {}".format(
                ", ".join(
                    "{}={}".format(key, value) for key, value in provided_values.items()
                )
            )

    user_can_execute_sql = request.user.has_perm("django_sql_dashboard.execute_sql")

    saved_dashboards = []
    if not dashboard:
        # Only show saved dashboards on index page
        saved_dashboards = [
            (dashboard, dashboard.user_can_edit(request.user))
            for dashboard in Dashboard.get_visible_to_user(request.user).select_related(
                "owned_by", "view_group", "edit_group"
            )
        ]

    context = {
        "title": title or "SQL Dashboard",
        "html_title": html_title,
        "query_results": query_results,
        "unverified_sql_queries": unverified_sql_queries,
        "available_tables": available_tables,
        "description": description,
        "dashboard": dashboard,
        "saved_dashboard": bool(dashboard),
        "user_owns_dashboard": dashboard and request.user == dashboard.owned_by,
        "user_can_edit_dashboard": dashboard and dashboard.user_can_edit(request.user),
        "user_can_execute_sql": user_can_execute_sql,
        "user_can_export_data": getattr(settings, "DASHBOARD_ENABLE_FULL_EXPORT", None)
        and user_can_execute_sql,
        "parameter_values": parameter_values.items(),
        "too_long_so_use_post": too_long_so_use_post,
        "saved_dashboards": saved_dashboards,
    }

    if extra_context:
        context.update(extra_context)

    response = render(
        request,
        template,
        context,
    )
    if request.user.is_authenticated:
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
    if view_policy == Dashboard.ViewPolicies.PRIVATE:
        if request.user != owner:
            return denied
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
        dashboard=dashboard,
        template="django_sql_dashboard/saved_dashboard.html",
    )


non_alpha_re = re.compile(r"[^a-zA-Z0-9]")


def export_sql_results(request):
    export_key = [k for k in request.POST.keys() if k.startswith("export_")][0]
    _, format, sql_index = export_key.split("_")
    assert format in ("csv", "tsv")
    sqls = request.POST.getlist("sql")
    sql = sqls[int(sql_index)]
    parameter_values = {
        parameter: request.POST.get(parameter, "")
        for parameter in extract_named_parameters(sql)
    }
    alias = getattr(settings, "DASHBOARD_DB_ALIAS", "dashboard")
    # Decide on filename
    sql_hash = hashlib.sha256(sql.encode("utf-8")).hexdigest()[:6]
    filename = non_alpha_re.sub("-", sql.lower()[:30]) + sql_hash

    filename_plus_ext = filename + "." + format

    connection = connections[alias]
    connection.cursor()  # To initialize connection
    cursor = connection.create_cursor(name="c" + filename.replace("-", "_"))

    csvfile = StringIO()
    csvwriter = csv.writer(
        csvfile,
        dialect={
            "csv": csv.excel,
            "tsv": csv.excel_tab,
        }[format],
    )

    def read_and_flush():
        csvfile.seek(0)
        data = csvfile.read()
        csvfile.seek(0)
        csvfile.truncate()
        return data

    def rows():
        try:
            cursor.execute(sql, parameter_values)
            done_header = False
            while True:
                records = cursor.fetchmany(size=2000)
                if not done_header:
                    csvwriter.writerow([r.name for r in cursor.description])
                    yield read_and_flush()
                    done_header = True
                if not records:
                    break
                for record in records:
                    csvwriter.writerow(record)
                    yield read_and_flush()
        finally:
            cursor.close()

    response = StreamingHttpResponse(
        rows(),
        content_type={
            "csv": "text/csv",
            "tsv": "text/tab-separated-values",
        }[format],
    )
    response["Content-Disposition"] = 'attachment; filename="' + filename_plus_ext + '"'
    return response
