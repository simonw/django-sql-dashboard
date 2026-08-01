import json

import pytest
from django.db import connections
from django.test.client import Client

from django_sql_dashboard.models import Dashboard

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


def rpc(client, method, params=None, id=1, headers=None):
    message = {"jsonrpc": "2.0", "id": id, "method": method}
    if params is not None:
        message["params"] = params
    return client.post(
        MCP_PATH,
        data=json.dumps(message),
        content_type="application/json",
        headers=headers,
    )


def call_tool(client, name, arguments=None):
    response = rpc(client, "tools/call", {"name": name, "arguments": arguments or {}})
    assert response.status_code == 200
    return response.json()["result"]


def tool_names(client):
    response = rpc(client, "tools/list")
    assert response.status_code == 200
    return [tool["name"] for tool in response.json()["result"]["tools"]]


def test_anonymous_clients_only_see_dashboard_tools(client, dashboard_db):
    assert tool_names(client) == ["list_dashboards", "execute_dashboard"]


def test_sql_tools_require_execute_sql_permission(
    client, dashboard_db, django_user_model, execute_sql_permission
):
    user = django_user_model.objects.create(username="mcp_user")
    client.force_login(user)
    # Without the permission: dashboard tools only, SQL calls are refused
    assert tool_names(client) == ["list_dashboards", "execute_dashboard"]
    result = call_tool(client, "execute_sql", {"sql": "select 1"})
    assert result["isError"] is True
    assert "You do not have permission to execute SQL" in result["content"][0]["text"]
    # Now grant the permission
    user.user_permissions.add(execute_sql_permission)
    client.force_login(user)
    assert tool_names(client) == [
        "list_tables",
        "get_schema",
        "execute_sql",
        "list_dashboards",
        "execute_dashboard",
    ]
    result = call_tool(client, "execute_sql", {"sql": "select 1 as one"})
    assert result["structuredContent"]["rows"] == [[1]]


def test_mcp_token_authentication(
    client, dashboard_db, settings, django_user_model, execute_sql_permission
):
    user = django_user_model.objects.create(username="token_user")
    user.user_permissions.add(execute_sql_permission)
    settings.DASHBOARD_MCP_TOKENS = {"correct-token": "token_user"}
    headers = {"authorization": "Bearer correct-token"}
    response = rpc(client, "tools/list", headers=headers)
    assert response.status_code == 200
    # And SQL can be executed
    response = rpc(
        client,
        "tools/call",
        {"name": "execute_sql", "arguments": {"sql": "select 1 as one"}},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["result"]["structuredContent"]["rows"] == [[1]]


@pytest.mark.parametrize(
    "authorization",
    (
        "Bearer wrong-token",
        "Bearer ",
        "Bearer correct-token-with-suffix",
    ),
)
def test_mcp_token_invalid_tokens_are_rejected(
    client, dashboard_db, settings, django_user_model, authorization
):
    django_user_model.objects.create(username="token_user")
    settings.DASHBOARD_MCP_TOKENS = {"correct-token": "token_user"}
    response = rpc(client, "tools/list", headers={"authorization": authorization})
    assert response.status_code == 401


def test_mcp_token_for_missing_user_is_rejected(client, dashboard_db, settings):
    settings.DASHBOARD_MCP_TOKENS = {"correct-token": "no_such_user"}
    response = rpc(
        client, "tools/list", headers={"authorization": "Bearer correct-token"}
    )
    assert response.status_code == 401


def test_mcp_token_for_inactive_user_is_rejected(
    client, dashboard_db, settings, django_user_model, execute_sql_permission
):
    user = django_user_model.objects.create(username="inactive_user", is_active=False)
    user.user_permissions.add(execute_sql_permission)
    settings.DASHBOARD_MCP_TOKENS = {"correct-token": "inactive_user"}
    response = rpc(
        client, "tools/list", headers={"authorization": "Bearer correct-token"}
    )
    assert response.status_code == 401


def test_mcp_token_user_still_needs_execute_sql_permission(
    client, dashboard_db, settings, django_user_model
):
    django_user_model.objects.create(username="powerless_user")
    settings.DASHBOARD_MCP_TOKENS = {"correct-token": "powerless_user"}
    headers = {"authorization": "Bearer correct-token"}
    response = rpc(
        client,
        "tools/call",
        {"name": "execute_sql", "arguments": {"sql": "select 1"}},
        headers=headers,
    )
    assert response.status_code == 200
    result = response.json()["result"]
    assert result["isError"] is True
    assert "You do not have permission to execute SQL" in result["content"][0]["text"]


def test_mcp_bearer_header_does_not_fall_back_to_session(admin_client, dashboard_db):
    # A logged-in session with an invalid Bearer token is still rejected
    response = rpc(
        admin_client, "tools/list", headers={"authorization": "Bearer wrong-token"}
    )
    assert response.status_code == 401


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
        "list_dashboards",
        "execute_dashboard",
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


def test_list_dashboards_anonymous_sees_only_public(client, dashboard_db):
    Dashboard.objects.create(slug="public-one", title="Public", view_policy="public")
    Dashboard.objects.create(slug="secret", view_policy="unlisted")
    Dashboard.objects.create(slug="private-one", view_policy="private")
    Dashboard.objects.create(slug="members", view_policy="loggedin")
    result = call_tool(client, "list_dashboards")
    assert result["isError"] is False
    assert result["structuredContent"] == {
        "dashboards": [
            {"slug": "public-one", "title": "Public", "description": ""},
        ]
    }


def test_list_dashboards_logged_in(client, dashboard_db, django_user_model):
    user = django_user_model.objects.create(username="viewer")
    Dashboard.objects.create(slug="public-one", view_policy="public")
    Dashboard.objects.create(slug="members", view_policy="loggedin")
    Dashboard.objects.create(slug="secret", view_policy="unlisted")
    Dashboard.objects.create(slug="mine", view_policy="private", owned_by=user)
    client.force_login(user)
    result = call_tool(client, "list_dashboards")
    slugs = [d["slug"] for d in result["structuredContent"]["dashboards"]]
    # Visible: loggedin, public and their own private - but never unlisted
    assert sorted(slugs) == ["members", "mine", "public-one"]


def test_execute_dashboard_anonymous_public(client, dashboard_db, saved_dashboard):
    result = call_tool(client, "execute_dashboard", {"slug": "test"})
    assert result["isError"] is False
    assert result["structuredContent"] == {
        "slug": "test",
        "title": "Test dashboard",
        "description": "This [supports markdown](http://example.com/)",
        "queries": [
            {
                "sql": "select 11 + 33",
                "columns": ["?column?"],
                "rows": [[44]],
                "truncated": False,
            },
            {
                "sql": "select 22 + 55",
                "columns": ["?column?"],
                "rows": [[77]],
                "truncated": False,
            },
        ],
    }


def test_execute_dashboard_unlisted_works_by_slug(client, dashboard_db):
    dashboard = Dashboard.objects.create(slug="secret", view_policy="unlisted")
    dashboard.queries.create(sql="select 1 as one")
    result = call_tool(client, "execute_dashboard", {"slug": "secret"})
    assert result["isError"] is False
    assert result["structuredContent"]["queries"][0]["rows"] == [[1]]


@pytest.mark.parametrize("slug", ("no-such-dashboard", "private-one", "members"))
def test_execute_dashboard_unavailable_dashboards_are_not_disclosed(
    client, dashboard_db, slug
):
    Dashboard.objects.create(slug="private-one", view_policy="private")
    Dashboard.objects.create(slug="members", view_policy="loggedin")
    result = call_tool(client, "execute_dashboard", {"slug": slug})
    assert result["isError"] is True
    assert (
        "Dashboard '{}' does not exist or is not available".format(slug)
        in result["content"][0]["text"]
    )


def test_execute_dashboard_owner_can_execute_private(
    client, dashboard_db, django_user_model
):
    user = django_user_model.objects.create(username="owner")
    dashboard = Dashboard.objects.create(
        slug="private-one", view_policy="private", owned_by=user
    )
    dashboard.queries.create(sql="select 1 as one")
    client.force_login(user)
    result = call_tool(client, "execute_dashboard", {"slug": "private-one"})
    assert result["isError"] is False
    assert result["structuredContent"]["queries"][0]["rows"] == [[1]]


def test_execute_dashboard_with_parameters(client, dashboard_db):
    dashboard = Dashboard.objects.create(slug="params", view_policy="public")
    dashboard.queries.create(sql="select %(name)s as name")
    result = call_tool(
        client,
        "execute_dashboard",
        {"slug": "params", "parameters": {"name": "Cleo"}},
    )
    assert result["structuredContent"]["queries"][0]["rows"] == [["Cleo"]]


def test_execute_dashboard_reports_per_query_errors(client, dashboard_db):
    dashboard = Dashboard.objects.create(slug="mixed", view_policy="public")
    dashboard.queries.create(sql="select * from no_such_table")
    dashboard.queries.create(sql="select 1 as one")
    result = call_tool(client, "execute_dashboard", {"slug": "mixed"})
    assert result["isError"] is False
    queries = result["structuredContent"]["queries"]
    assert 'relation "no_such_table" does not exist' in queries[0]["error"]
    assert queries[1]["rows"] == [[1]]


def test_execute_dashboard_does_not_require_execute_sql_permission(
    client, dashboard_db, django_user_model, saved_dashboard
):
    user = django_user_model.objects.create(username="powerless_viewer")
    client.force_login(user)
    result = call_tool(client, "execute_dashboard", {"slug": "test"})
    assert result["isError"] is False
    assert result["structuredContent"]["queries"][0]["rows"] == [[44]]
