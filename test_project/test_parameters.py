from urllib.parse import urlencode

import pytest
from django.core import signing

from django_sql_dashboard.models import Dashboard
from django_sql_dashboard.utils import sign_sql


def test_parameter_form(admin_client, dashboard_db):
    response = admin_client.get(
        "/dashboard/?"
        + urlencode(
            {
                "sql": signed_sql(
                    [
                        "select %(foo)s as foo, %(bar)s as bar",
                        "select select %(foo)s as foo, select %(baz)s as baz",
                    ]
                )
            },
            doseq=True,
        )
    )
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    # Form should have three form fields
    for fragment in (
        '<label for="qp_foo">foo</label>',
        '<input type="text" id="qp_foo" name="foo" value="">',
        '<label for="qp_bar">bar</label>',
        '<input type="text" id="qp_bar" name="bar" value="">',
        '<label for="qp_baz">baz</label>',
        '<input type="text" id="qp_baz" name="baz" value="">',
    ):
        assert fragment in html


def test_parameters_applied(admin_client, dashboard_db):
    response = admin_client.get(
        "/dashboard/?"
        + urlencode(
            {
                "sql": signed_sql(
                    [
                        "select %(foo)s || '!' as exclaim",
                        "select %(foo)s || '! ' || %(bar)s || '!!' as double_exclaim",
                    ]
                ),
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


def signed_sql(queries):
    return [sign_sql(sql) for sql in queries]
