from django_sql_dashboard.models import Dashboard
from django_sql_dashboard.utils import SQL_SALT
from django.core import signing
import urllib.parse


def test_dashboard_submit_sql(admin_client, dashboard_db):
    # Test full flow of POST submitting new SQL, having it signed
    # and having it redirect to the results page
    assert admin_client.get("/dashboard/").status_code == 200
    sql = "select 14 + 33"
    response = admin_client.post("/dashboard/", {"sql": sql})
    assert response.status_code == 302
    # Should redirect to ?sql=signed-value
    signed_sql = urllib.parse.parse_qs(response.url.split("?")[1])["sql"][0]
    assert signed_sql == signing.dumps(sql, salt=SQL_SALT)
    # GET against this new location should return correct result
    get_response = admin_client.get(response.url)
    assert get_response.status_code == 200
    assert b"47" in get_response.content


def test_saved_dashboard(client, admin_client, dashboard_db):
    assert admin_client.get("/dashboard/test/").status_code == 404
    dashboard = Dashboard.objects.create(slug="test")
    dashboard.queries.create(sql="select 11 + 33")
    dashboard.queries.create(sql="select 22 + 55")
    response = admin_client.get("/dashboard/test/")
    assert response.status_code == 200
    assert b"44" in response.content
    assert b"77" in response.content
    assert b">count<" in response.content


def test_many_long_column_names(admin_client, dashboard_db):
    # https://github.com/simonw/django-sql-dashboard/issues/23
    columns = ["column{}".format(i) for i in range(200)]
    sql = "select " + ", ".join(
        "'{}' as {}".format(column, column) for column in columns
    )
    response = admin_client.post("/dashboard/", {"sql": sql}, follow=True)
    assert response.status_code == 200
