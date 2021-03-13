import json
import time

from django.contrib.auth.decorators import permission_required
from django.db import connection, transaction
from django.shortcuts import get_object_or_404, render

from .models import Dashboard


@permission_required("django_sql_dashboard.execute_sql")
def dashboard_index(request):
    sql_queries = [q for q in request.GET.getlist("sql") if q.strip()]
    return _dashboard_index(request, sql_queries, title="Django SQL Dashboard")


def _dashboard_index(
    request, sql_queries, title=None, description=None, saved_dashboard=False
):
    query_results = []
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
    if sql_queries:
        for sql in sql_queries:
            sql = sql.strip()
            if ";" in sql.rstrip(";"):
                query_results.append(
                    {
                        "sql": sql,
                        "rows": [],
                        "description": [],
                        "truncated": False,
                        "error": "';' not allowed in SQL queries",
                    }
                )
                continue
            with transaction.atomic():
                with connection.cursor() as cursor:
                    duration_ms = None
                    try:
                        start = time.perf_counter()
                        cursor.execute("SET TRANSACTION READ ONLY;")
                        # Running a SELECT prevents future SET TRANSACTION READ WRITE:
                        cursor.execute("SELECT 1;")
                        cursor.execute(sql)
                        rows = list(cursor.fetchmany(101))
                        duration_ms = (time.perf_counter() - start) * 1000.0
                    except Exception as e:
                        query_results.append(
                            {
                                "sql": sql,
                                "rows": [],
                                "description": [],
                                "truncated": False,
                                "error": str(e),
                            }
                        )
                    else:
                        query_results.append(
                            {
                                "sql": sql,
                                "rows": displayable_rows(rows[:100]),
                                "description": cursor.description,
                                "truncated": len(rows) == 101,
                                "duration_ms": duration_ms,
                            }
                        )
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
        },
    )


def dashboard(request, slug):
    dashboard = get_object_or_404(Dashboard, slug=slug)
    return _dashboard_index(
        request,
        sql_queries=[query.sql for query in dashboard.queries.all()],
        title=dashboard.title,
        description=dashboard.description,
        saved_dashboard=True,
    )


def displayable_rows(rows):
    fixed = []
    for row in rows:
        fixed_row = []
        for cell in row:
            if isinstance(cell, (dict, list)):
                cell = json.dumps(cell)
            fixed_row.append(cell)
        fixed.append(fixed_row)
    return fixed
