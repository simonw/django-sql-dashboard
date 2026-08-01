"""
A Model Context Protocol (MCP) server for django-sql-dashboard.

This implements the stateless variant of the MCP Streamable HTTP transport
as a single Django view, without any additional dependencies. It exposes
three read-only tools:

- list_tables - list the tables visible to the dashboard connection
- get_schema - return the schema (tables, columns, types) for the database
- execute_sql - execute one read-only SQL query and return its results

SQL execution uses the same protected path as the dashboard views: the
read-only "dashboard" database alias, a transaction that is rolled back,
the ``DASHBOARD_ROW_LIMIT`` row limit and the same named parameter support.
Callers must be authenticated and have the
``django_sql_dashboard.execute_sql`` permission.

Inspired by https://github.com/datasette/datasette-mcp
"""

import json
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connections
from django.db.utils import ProgrammingError
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .utils import displayable_rows, extract_named_parameters

MCP_PROTOCOL_VERSION = "2025-06-18"

SERVER_INFO = {
    "name": "django-sql-dashboard",
    "version": "1.2",
}

SERVER_INSTRUCTIONS = (
    "Call list_tables, then get_schema to see columns and types, "
    "then execute_sql to answer questions using read-only PostgreSQL."
)

TABLES_AND_COLUMNS_SQL = """
select
  information_schema.columns.table_name,
  cast(column_name as text),
  cast(data_type as text)
from
  information_schema.columns
join
  information_schema.tables on
  information_schema.columns.table_name = information_schema.tables.table_name
  and information_schema.tables.table_schema = 'public'
where
  information_schema.columns.table_schema = 'public'
order by
  information_schema.columns.table_name,
  information_schema.columns.ordinal_position
"""


class ToolError(Exception):
    "An expected, recoverable tool failure - returned as isError content"


def _dashboard_connection():
    alias = getattr(settings, "DASHBOARD_DB_ALIAS", "dashboard")
    return connections[alias]


def _tables_and_columns():
    # Returns [(table_name, [(column, data_type), ...]), ...]
    tables = []
    with _dashboard_connection().cursor() as cursor:
        cursor.execute(TABLES_AND_COLUMNS_SQL)
        for table_name, column, data_type in cursor.fetchall():
            if not tables or tables[-1][0] != table_name:
                tables.append((table_name, []))
            tables[-1][1].append((column, data_type))
    return tables


def tool_list_tables():
    return {"tables": [table for table, _ in _tables_and_columns()]}


def tool_get_schema():
    blocks = []
    for table, columns in _tables_and_columns():
        column_lines = ",\n".join(
            "  {} {}".format(column, data_type) for column, data_type in columns
        )
        blocks.append("{} (\n{}\n)".format(table, column_lines))
    return {"schema": "\n\n".join(blocks)}


def _serialize_cell(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, memoryview):
        value = value.tobytes()
    if isinstance(value, bytes):
        return {"hex": value.hex()}
    return str(value)


def tool_execute_sql(sql, parameters=None):
    sql = sql.strip().rstrip(";")
    if not sql:
        raise ToolError("SQL query is required")
    if ";" in sql:
        raise ToolError("';' not allowed in SQL queries")
    try:
        extracted_parameters = extract_named_parameters(sql)
    except ValueError:
        raise ToolError(r"Invalid query - try escaping single '%' as double '%%'")
    parameter_values = {
        parameter: str((parameters or {}).get(parameter, ""))
        for parameter in extracted_parameters
    }
    row_limit = getattr(settings, "DASHBOARD_ROW_LIMIT", None) or 100
    connection = _dashboard_connection()
    with connection.cursor() as cursor:
        try:
            cursor.execute("BEGIN;")
            # Running a SELECT prevents future SET TRANSACTION READ WRITE:
            cursor.execute("SELECT 1;")
            cursor.fetchall()
            cursor.execute(sql, parameter_values)
            try:
                rows = list(cursor.fetchmany(row_limit + 1))
                columns = [c.name for c in cursor.description]
            except ProgrammingError:
                rows = [[str(cursor.statusmessage)]]
                columns = ["statusmessage"]
        except Exception as e:
            raise ToolError(str(e))
        finally:
            cursor.execute("ROLLBACK;")
    return {
        "columns": columns,
        "rows": [
            [_serialize_cell(cell) for cell in row]
            for row in displayable_rows(rows[:row_limit])
        ],
        "truncated": len(rows) == row_limit + 1,
    }


TOOLS = [
    {
        "name": "list_tables",
        "description": "List the tables available to SQL queries in this dashboard.",
        "handler": tool_list_tables,
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "tables": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["tables"],
        },
    },
    {
        "name": "get_schema",
        "description": (
            "Return the schema for the dashboard database: every table with "
            "its columns and their PostgreSQL types. Call this before "
            "constructing a SQL query."
        ),
        "handler": tool_get_schema,
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "schema": {"type": "string"},
            },
            "required": ["schema"],
        },
    },
    {
        "name": "execute_sql",
        "description": (
            "Execute one read-only PostgreSQL SELECT query and return its "
            "columns and rows. Use %(name)s placeholders in the SQL and pass "
            "their values in the parameters argument. The ';' character is "
            "not allowed. Results are truncated to the dashboard row limit."
        ),
        "handler": tool_execute_sql,
        "inputSchema": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "The PostgreSQL SELECT query to execute",
                },
                "parameters": {
                    "type": "object",
                    "description": (
                        "Values for any %(name)s parameters used in the SQL"
                    ),
                    "additionalProperties": {"type": "string"},
                },
            },
            "required": ["sql"],
            "additionalProperties": False,
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "columns": {"type": "array", "items": {"type": "string"}},
                "rows": {"type": "array", "items": {"type": "array"}},
                "truncated": {"type": "boolean"},
            },
            "required": ["columns", "rows", "truncated"],
        },
    },
]

TOOLS_BY_NAME = {tool["name"]: tool for tool in TOOLS}


def _jsonrpc_response(id, result):
    return JsonResponse({"jsonrpc": "2.0", "id": id, "result": result})


def _jsonrpc_error(id, code, message, status=200):
    return JsonResponse(
        {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}},
        status=status,
    )


def _handle_initialize(params):
    return {
        "protocolVersion": MCP_PROTOCOL_VERSION,
        "capabilities": {"tools": {}},
        "serverInfo": SERVER_INFO,
        "instructions": SERVER_INSTRUCTIONS,
    }


def _handle_tools_list(params):
    return {
        "tools": [
            {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": tool["inputSchema"],
                "outputSchema": tool["outputSchema"],
                "annotations": {"readOnlyHint": True, "openWorldHint": False},
            }
            for tool in TOOLS
        ]
    }


def _handle_tools_call(params):
    name = params.get("name")
    tool = TOOLS_BY_NAME.get(name)
    if tool is None:
        raise KeyError("Unknown tool: {}".format(name))
    arguments = params.get("arguments") or {}
    try:
        structured = tool["handler"](**arguments)
    except ToolError as e:
        return {
            "content": [{"type": "text", "text": str(e)}],
            "isError": True,
        }
    return {
        "content": [
            {"type": "text", "text": json.dumps(structured, default=str)},
        ],
        "structuredContent": structured,
        "isError": False,
    }


METHODS = {
    "initialize": _handle_initialize,
    "ping": lambda params: {},
    "tools/list": _handle_tools_list,
    "tools/call": _handle_tools_call,
}


def _user_for_bearer_token(token):
    # Returns the user for a DASHBOARD_MCP_TOKENS token, or None
    tokens = getattr(settings, "DASHBOARD_MCP_TOKENS", None) or {}
    username = None
    for configured_token, configured_username in tokens.items():
        # compare_digest to avoid leaking token prefixes via timing
        if secrets.compare_digest(str(configured_token), token):
            username = configured_username
    if username is None:
        return None
    UserModel = get_user_model()
    try:
        user = UserModel._default_manager.get_by_natural_key(username)
    except UserModel.DoesNotExist:
        return None
    if not user.is_active:
        return None
    return user


def _authenticate(request):
    # Returns (user, error_response) - exactly one is not None
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        user = _user_for_bearer_token(authorization[len("Bearer ") :].strip())
        if user is None:
            return None, JsonResponse({"error": "Invalid token"}, status=401)
        return user, None
    if request.user.is_authenticated:
        return request.user, None
    return None, JsonResponse({"error": "Authentication required"}, status=401)


@csrf_exempt
def mcp_endpoint(request):
    user, error_response = _authenticate(request)
    if error_response is not None:
        return error_response
    if not user.has_perm("django_sql_dashboard.execute_sql"):
        return JsonResponse(
            {"error": "You do not have permission to execute SQL"}, status=403
        )
    if request.method != "POST":
        response = JsonResponse({"error": "Method not allowed"}, status=405)
        response["Allow"] = "POST"
        return response
    try:
        message = json.loads(request.body)
    except ValueError:
        return _jsonrpc_error(None, -32700, "Parse error", status=400)
    if not isinstance(message, dict):
        return _jsonrpc_error(None, -32600, "Invalid request", status=400)
    method = message.get("method")
    if "id" not in message:
        # A notification - accept it without a response
        return HttpResponse(status=202)
    id = message["id"]
    handler = METHODS.get(method)
    if handler is None:
        return _jsonrpc_error(id, -32601, "Method not found: {}".format(method))
    try:
        result = handler(message.get("params") or {})
    except (TypeError, KeyError) as e:
        return _jsonrpc_error(id, -32602, "Invalid params: {}".format(e))
    return _jsonrpc_response(id, result)
