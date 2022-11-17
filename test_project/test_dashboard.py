import urllib.parse

import pytest
from bs4 import BeautifulSoup
from django.core import signing
from django.db import connections

from django_sql_dashboard.utils import SQL_SALT, is_valid_base64_json, sign_sql


def test_dashboard_submit_sql(admin_client, dashboard_db):
    # Test full flow of POST submitting new SQL, having it signed
    # and having it redirect to the results page
    get_response = admin_client.get("/dashboard/")
    assert get_response.status_code == 200
    assert get_response["Content-Security-Policy"] == "frame-ancestors 'self'"
    sql = "select 14 + 33"
    response = admin_client.post(
        "/dashboard/",
        {
            "sql": sql,
            "_save-title": "",
            "_save-slug": "",
            "_save-description": "",
            "_save-view_policy": "private",
            "_save-view_group": "",
            "_save-edit_policy": "private",
            "_save-edit_group": "",
        },
    )
    assert response.status_code == 302
    # Should redirect to ?sql=signed-value
    bits = urllib.parse.parse_qs(response.url.split("?")[1])
    assert set(bits.keys()) == {"sql"}
    signed_sql = bits["sql"][0]
    assert signed_sql == sign_sql(sql)
    # GET against this new location should return correct result
    get_response = admin_client.get(response.url)
    assert get_response.status_code == 200
    assert b"47" in get_response.content


def test_invalid_signature_shows_warning(admin_client, dashboard_db):
    response1 = admin_client.post("/dashboard/", {"sql": "select 1 + 1"})
    signed_sql = urllib.parse.parse_qs(response1.url.split("?")[1])["sql"][0]
    # Break the signature and load the page
    response2 = admin_client.get(
        "/dashboard/?" + urllib.parse.urlencode({"sql": signed_sql[:-1]})
    )
    html = response2.content.decode("utf-8")
    assert ">Unverified SQL<" in html
    assert "<textarea>select 1 + 1</textarea>" in html


def test_dashboard_upgrade_old_base64_links(admin_client, dashboard_db, settings):
    old_signed = signing.dumps("select 1 + 1", salt=SQL_SALT)
    assert is_valid_base64_json(old_signed.split(":")[0])
    # Should do nothing without setting
    assert admin_client.get("/dashboard/?sql=" + old_signed).status_code == 200
    # With setting should redirect
    settings.DASHBOARD_UPGRADE_OLD_BASE64_LINKS = True
    response = admin_client.get("/dashboard/?sql=" + old_signed)
    assert response.status_code == 302
    assert response.url == "/dashboard/?" + urllib.parse.urlencode(
        {"sql": sign_sql("select 1 + 1")}
    )


def test_dashboard_upgrade_does_not_break_regular_pages(
    admin_client, dashboard_db, settings
):
    # With setting should redirect
    settings.DASHBOARD_UPGRADE_OLD_BASE64_LINKS = True
    response = admin_client.get("/dashboard/")
    assert response.status_code == 200


def test_saved_dashboard(client, admin_client, dashboard_db, saved_dashboard):
    assert admin_client.get("/dashboard/test2/").status_code == 404
    response = admin_client.get("/dashboard/test/")
    assert response.status_code == 200
    assert b"44" in response.content
    assert b"77" in response.content
    assert b"data-count-url" in response.content
    # And test markdown support
    assert (
        b'<a href="http://example.com/" rel="nofollow">supports markdown</a>'
        in response.content
    )


def test_many_long_column_names(admin_client, dashboard_db):
    # https://github.com/simonw/django-sql-dashboard/issues/23
    columns = ["column{}".format(i) for i in range(200)]
    sql = "select " + ", ".join(
        "'{}' as {}".format(column, column) for column in columns
    )
    response = admin_client.post("/dashboard/", {"sql": sql}, follow=True)
    assert response.status_code == 200


@pytest.mark.parametrize(
    "sql,expected_error",
    (
        (
            "select * from not_a_table",
            'relation "not_a_table" does not exist\nLINE 1: select * from not_a_table\n                      ^',
        ),
        (
            "select 'foo' like 'f%'",
            r"Invalid query - try escaping single '%' as double '%%'",
        ),
        (
            "select '% completed'",
            r"Invalid query - try escaping single '%' as double '%%'",
        ),
    ),
)
def test_dashboard_sql_errors(admin_client, sql, expected_error):
    response = admin_client.post("/dashboard/", {"sql": sql}, follow=True)
    assert response.status_code == 200
    soup = BeautifulSoup(response.content, "html5lib")
    div = soup.select(".query-results")[0]
    assert div["class"] == ["query-results", "query-error"]
    assert div.select(".error-message")[0].text.strip() == expected_error


@pytest.mark.parametrize(
    "sql,expected_columns,expected_rows",
    (
        ("select 'abc' as one, 'bcd' as one", ["one", "one"], [["abc", "bcd"]]),
        ("select ARRAY[1, 2, 3]", ["array"], [["[\n  1,\n  2,\n  3\n]"]]),
        (
            "select ARRAY[TIMESTAMP WITH TIME ZONE '2004-10-19 10:23:54+02']",
            ["array"],
            [['[\n  "2004-10-19 08:23:54+00:00"\n]']],
        ),
    ),
)
def test_dashboard_sql_queries(admin_client, sql, expected_columns, expected_rows):
    response = admin_client.post("/dashboard/", {"sql": sql}, follow=True)
    assert response.status_code == 200
    soup = BeautifulSoup(response.content, "html5lib")
    div = soup.select(".query-results")[0]
    columns = [th.text.split(" [")[0] for th in div.findAll("th")]
    trs = div.find("tbody").findAll("tr")
    rows = [[td.text for td in tr.findAll("td")] for tr in trs]
    assert columns == expected_columns
    assert rows == expected_rows


def test_dashboard_uses_post_if_sql_is_too_long(admin_client):
    # Queries longer than 1800 characters do not redirect to GET
    short_sql = "select %(start)s::integer + "
    long_sql = "select %(start)s::integer + " + "+".join(["1"] * 1801)
    assert (
        admin_client.post("/dashboard/", {"sql": short_sql, "start": 100}).status_code
        == 302
    )
    response = admin_client.post("/dashboard/", {"sql": long_sql, "start": 100})
    assert response.status_code == 200
    assert b"1901" in response.content
    # And should not have 'count' links
    assert b"data-count-url=" not in response.content


@pytest.mark.parametrize(
    "path,sqls,args,expected_title",
    (
        ("/dashboard/", [], None, "SQL Dashboard"),
        ("/dashboard/", ["select 1"], None, "SQL: select 1"),
        (
            "/dashboard/",
            ["select %(name)s"],
            {"name": "test"},
            "SQL: select %(name)s: test",
        ),
        (
            "/dashboard/",
            ["select %(name)s, %(age)s"],
            {"name": "test", "age": 5},
            "SQL: select %(name)s, %(age)s: name=test, age=5",
        ),
        ("/dashboard/", ["select 1", "select 2"], None, "SQL: select 1 [,] select 2"),
        ("/dashboard/test/", [], None, "Test dashboard"),
        ("/dashboard/test/", [], {"name": "claire"}, "Test dashboard: claire"),
    ),
)
def test_dashboard_html_title(
    admin_client, saved_dashboard, path, args, sqls, expected_title
):
    saved_dashboard.queries.create(sql="select %(name)s")
    args = args or {}
    if sqls:
        args["sql"] = sqls
        response = admin_client.post(path, args, follow=True)
    else:
        response = admin_client.get(path, data=args)
    soup = BeautifulSoup(response.content, "html5lib")
    assert soup.find("title").text == expected_title


def test_saved_dashboard_errors_sql_not_in_textarea(admin_client, saved_dashboard):
    saved_dashboard.queries.create(sql="this is bad")
    response = admin_client.get("/dashboard/test/")
    html = response.content.decode("utf-8")
    assert '<pre class="sql">this is bad</pre>' in html


def test_dashboard_show_available_tables(admin_client):
    response = admin_client.get("/dashboard/")
    soup = BeautifulSoup(response.content, "html5lib")
    lis = soup.find("ul").findAll("li")
    details = [
        {
            "table": li.find("a").text,
            "columns": li.find("p").text,
            "href": li.find("a")["href"],
        }
        for li in lis
        if li.find("a").text.startswith("django_sql_dashboard")
        or li.find("a").text == "switches"
    ]
    # Decode the href in each one into a SQL query
    for detail in details:
        href = detail.pop("href")
        detail["href_sql"] = urllib.parse.parse_qs(href)["sql"][0].rsplit(":", 1)[0]
    assert details == [
        {
            "table": "django_sql_dashboard_dashboard",
            "columns": "id, slug, title, description, created_at, edit_group_id, edit_policy, owned_by_id, view_group_id, view_policy",
            "href_sql": "select id, slug, title, description, created_at, edit_group_id, edit_policy, owned_by_id, view_group_id, view_policy from django_sql_dashboard_dashboard",
        },
        {
            "table": "django_sql_dashboard_dashboardquery",
            "columns": "id, sql, dashboard_id, _order",
            "href_sql": "select id, sql, dashboard_id, _order from django_sql_dashboard_dashboardquery",
        },
        {
            "table": "switches",
            "columns": "id, name, on",
            "href_sql": 'select id, name, "on" from switches',
        },
    ]
