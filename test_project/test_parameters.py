import pytest
from urllib.parse import urlencode
from django_sql_dashboard.models import Dashboard


def test_parameter_form(admin_client, dashboard_db):
    response = admin_client.get(
        "/dashboard/?"
        + urlencode(
            {
                "sql": [
                    "select %(foo)s as foo, %(bar)s as bar",
                    "select select %(foo)s as foo, select %(baz)s as baz",
                ]
            },
            doseq=True,
        )
    )
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    # Form should have three form fields
    for fragment in (
        '<label for="qp1">foo</label>',
        '<input type="text" id="qp1" name="foo" value="">',
        '<label for="qp2">bar</label>',
        '<input type="text" id="qp2" name="bar" value="">',
        '<label for="qp3">baz</label>',
        '<input type="text" id="qp3" name="baz" value="">',
    ):
        assert fragment in html


def test_parameters_applied(admin_client, dashboard_db):
    response = admin_client.get(
        "/dashboard/?"
        + urlencode(
            {
                "sql": [
                    "select %(foo)s || '!' as exclaim",
                    "select %(foo)s || '! ' || %(bar)s || '!!' as double_exclaim",
                ],
                "foo": "FOO",
                "bar": "BAR",
            },
            doseq=True,
        )
    )
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert "<td>FOO!</td>" in html
    assert "<td>FOO! BAR!!</td>" in html
