import json

import pytest
from django.db import connections
from django.test.client import Client

MCP_PATH = "/dashboard/-/mcp"


@pytest.fixture
def writable_dashboard_db():
    # Reconnect the dashboard alias with no connection options, so the
    # transactional test teardown flush can TRUNCATE tables afterwards
    connection = connections["dashboard"]
    connection.close()
    connection.settings_dict.setdefault("OPTIONS", {}).pop("options", None)
    yield
    connection.close()


@pytest.fixture
def read_only_dashboard_db(writable_dashboard_db):
    # Reconnect the dashboard alias with the read-only option applied, to
    # match the recommended production configuration
    connection = connections["dashboard"]
    options = connection.settings_dict["OPTIONS"]
    options["options"] = "-c default_transaction_read_only=on"
    yield
    connection.close()
    options.pop("options", None)


def rpc(client, method, params=None, id=1):
    message = {"jsonrpc": "2.0", "id": id, "method": method}
    if params is not None:
        message["params"] = params
    return client.post(
        MCP_PATH, data=json.dumps(message), content_type="application/json"
    )


def call_tool(client, name, arguments=None):
    response = rpc(client, "tools/call", {"name": name, "arguments": arguments or {}})
    assert response.status_code == 200
    return response.json()["result"]


def test_mcp_requires_authentication(client, dashboard_db):
    response = rpc(client, "tools/list")
    assert response.status_code == 401


def test_mcp_requires_execute_sql_permission(
    client, dashboard_db, django_user_model, execute_sql_permission
):
    user = django_user_model.objects.create(username="mcp_user")
    client.force_login(user)
    assert rpc(client, "tools/list").status_code == 403
    # Now grant the permission
    user.user_permissions.add(execute_sql_permission)
    user = django_user_model.objects.get(pk=user.pk)  # to clear permission cache
    client.force_login(user)
    assert rpc(client, "tools/list").status_code == 200


def test_mcp_is_csrf_exempt(admin_client, dashboard_db, admin_user):
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(admin_user)
    assert rpc(csrf_client, "ping").status_code == 200


def test_initialize(admin_client, dashboard_db):
    response = rpc(admin_client, "initialize")
    assert response.status_code == 200
    result = response.json()["result"]
    assert result["protocolVersion"] == "2025-06-18"
    assert result["capabilities"] == {"tools": {}}
    assert result["serverInfo"]["name"] == "django-sql-dashboard"
    assert result["instructions"]


def test_notifications_are_accepted(admin_client, dashboard_db):
    response = admin_client.post(
        MCP_PATH,
        data=json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
        content_type="application/json",
    )
    assert response.status_code == 202


def test_unknown_method_returns_error(admin_client, dashboard_db):
    response = rpc(admin_client, "resources/list")
    assert response.status_code == 200
    error = response.json()["error"]
    assert error["code"] == -32601


def test_invalid_json_returns_parse_error(admin_client, dashboard_db):
    response = admin_client.post(
        MCP_PATH, data="this is not json", content_type="application/json"
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == -32700


def test_get_is_not_allowed(admin_client, dashboard_db):
    response = admin_client.get(MCP_PATH)
    assert response.status_code == 405
    assert response["Allow"] == "POST"


def test_tools_list(admin_client, dashboard_db):
    response = rpc(admin_client, "tools/list")
    assert response.status_code == 200
    tools = response.json()["result"]["tools"]
    assert [tool["name"] for tool in tools] == [
        "list_tables",
        "get_schema",
        "execute_sql",
    ]
    for tool in tools:
        assert tool["description"]
        assert tool["inputSchema"]
        assert tool["outputSchema"]
        assert tool["annotations"] == {"readOnlyHint": True, "openWorldHint": False}


def test_list_tables(admin_client, dashboard_db):
    result = call_tool(admin_client, "list_tables")
    assert result["isError"] is False
    tables = result["structuredContent"]["tables"]
    assert "django_sql_dashboard_dashboard" in tables
    assert tables == sorted(tables)


def test_get_schema(admin_client, dashboard_db):
    result = call_tool(admin_client, "get_schema")
    assert result["isError"] is False
    schema = result["structuredContent"]["schema"]
    assert "django_sql_dashboard_dashboard (" in schema
    assert "slug character varying" in schema


def test_execute_sql(admin_client, dashboard_db):
    result = call_tool(
        admin_client, "execute_sql", {"sql": "select 1 + 2 as total, 'hi' as greeting"}
    )
    assert result["isError"] is False
    assert result["structuredContent"] == {
        "columns": ["total", "greeting"],
        "rows": [[3, "hi"]],
        "truncated": False,
    }
    # The text content should be the JSON-encoded structured content
    assert json.loads(result["content"][0]["text"]) == result["structuredContent"]


def test_execute_sql_with_parameters(admin_client, dashboard_db):
    result = call_tool(
        admin_client,
        "execute_sql",
        {
            "sql": "select %(name)s as name",
            "parameters": {"name": "Cleo"},
        },
    )
    assert result["structuredContent"]["rows"] == [["Cleo"]]


def test_execute_sql_truncates_at_row_limit(admin_client, dashboard_db, settings):
    settings.DASHBOARD_ROW_LIMIT = 5
    result = call_tool(
        admin_client, "execute_sql", {"sql": "select * from generate_series(1, 10)"}
    )
    assert result["structuredContent"]["rows"] == [[1], [2], [3], [4], [5]]
    assert result["structuredContent"]["truncated"] is True


@pytest.mark.parametrize(
    "sql,expected_error",
    (
        ("select 1; select 2", "';' not allowed in SQL queries"),
        ("", "SQL query is required"),
        ("select 100% of results", "Invalid query"),
        ("select * from no_such_table", 'relation "no_such_table" does not exist'),
    ),
)
def test_execute_sql_errors(admin_client, dashboard_db, sql, expected_error):
    result = call_tool(admin_client, "execute_sql", {"sql": sql})
    assert result["isError"] is True
    assert expected_error in result["content"][0]["text"]


@pytest.mark.django_db(databases=["default", "dashboard"], transaction=True)
@pytest.mark.parametrize(
    "sql",
    (
        "create table forbidden (id integer)",
        "delete from auth_user",
        "update auth_user set username = 'hacked'",
    ),
)
def test_execute_sql_rejects_writes_on_read_only_connection(
    admin_client, read_only_dashboard_db, sql
):
    result = call_tool(admin_client, "execute_sql", {"sql": sql})
    assert result["isError"] is True
    assert "read-only transaction" in result["content"][0]["text"]
    # A subsequent valid read still succeeds
    result = call_tool(admin_client, "execute_sql", {"sql": "select 1 as value"})
    assert result["structuredContent"]["rows"] == [[1]]


@pytest.mark.django_db(databases=["default", "dashboard"], transaction=True)
def test_execute_sql_writes_are_rolled_back(admin_client, writable_dashboard_db):
    # Even without a read-only connection, the wrapping transaction is
    # always rolled back so writes never stick
    from django_sql_dashboard.models import Dashboard

    Dashboard.objects.create(slug="rollback-test")
    count_sql = "select count(*) from django_sql_dashboard_dashboard"
    result = call_tool(admin_client, "execute_sql", {"sql": count_sql})
    count = result["structuredContent"]["rows"][0][0]
    assert count == 1
    call_tool(
        admin_client,
        "execute_sql",
        {"sql": "delete from django_sql_dashboard_dashboard"},
    )
    result = call_tool(admin_client, "execute_sql", {"sql": count_sql})
    assert result["structuredContent"]["rows"][0][0] == count


def test_unknown_tool_returns_invalid_params(admin_client, dashboard_db):
    response = rpc(admin_client, "tools/call", {"name": "drop_tables", "arguments": {}})
    assert response.status_code == 200
    assert response.json()["error"]["code"] == -32602
