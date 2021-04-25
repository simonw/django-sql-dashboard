from urllib.parse import parse_qsl

import pytest
from bs4 import BeautifulSoup
from django.core import signing

from django_sql_dashboard.utils import unsign_sql


def test_default_widget(admin_client, dashboard_db):
    response = admin_client.post(
        "/dashboard/",
        {
            "sql": """
            SELECT * FROM (
                VALUES (1, 'one', 4.5), (2, 'two', 3.6), (3, 'three', 4.1)
            ) AS t (id, name, size)"""
        },
        follow=True,
    )
    html = response.content.decode("utf-8")
    soup = BeautifulSoup(html, "html5lib")
    assert soup.find("textarea").text == (
        "SELECT * FROM (\n"
        "                VALUES (1, 'one', 4.5), (2, 'two', 3.6), (3, 'three', 4.1)\n"
        "            ) AS t (id, name, size)"
    )
    # Copyable area:
    assert soup.select("textarea#copyable-0")[0].text == (
        "id\tname\tsize\n" "1\tone\t4.5\n" "2\ttwo\t3.6\n" "3\tthree\t4.1"
    )


def test_basic_table_with_some_links(admin_client, dashboard_db):
    response = admin_client.post(
        "/dashboard/",
        {
            "sql": """
            SELECT
                'https://www.google.com/' as google,
                'http://www.yahoo.com/' as yahoo,
                'www.bing.com/' as bing,
                123 as number,
                'foop' as string,
                null as this_is_null
            """
        },
        follow=True,
    )
    html = response.content.decode("utf-8")
    soup = BeautifulSoup(html, "html5lib")
    trs = soup.select("table tbody tr")
    row = trs[0]
    tds_html = [str(td) for td in row.select("td")]
    assert tds_html == [
        '<td><a href="https://www.google.com/" rel="nofollow">https://www.google.com/</a></td>',
        '<td><a href="http://www.yahoo.com/" rel="nofollow">http://www.yahoo.com/</a></td>',
        '<td><a href="http://www.bing.com/" rel="nofollow">www.bing.com/</a></td>',
        "<td>123</td>",
        "<td>foop</td>",
        '<td><span class="null">- null -</span></td>',
    ]


def test_default_widget_column_count_links(admin_client, dashboard_db):
    response = admin_client.post(
        "/dashboard/",
        {
            "sql": """
            SELECT * FROM (
                VALUES (1, %(label)s, 4.5), (2, 'two', 3.6), (3, 'three', 4.1)
            ) AS t (id, name, size)""",
            "label": "LABEL",
        },
        follow=True,
    )
    soup = BeautifulSoup(response.content, "html5lib")
    # Check that first link
    link = soup.select("thead th a")[0]
    assert link.text == "count"
    querystring = link["href"].split("?")[1]
    bits = dict(parse_qsl(querystring))
    assert unsign_sql(bits["sql"])[0] == (
        'select "id", count(*) as n from (SELECT * FROM (\n'
        "                VALUES (1, %(label)s, 4.5), "
        "(2, 'two', 3.6), (3, 'three', 4.1)\n"
        "            ) AS t (id, name, size))"
        ' as results group by "id" order by n desc'
    )
    assert bits["label"] == "LABEL"


@pytest.mark.parametrize(
    "sql,should_have_count_links",
    (
        ("SELECT 1 AS id, 2 AS id", False),
        ("SELECT 1 AS id, 2 AS id2", True),
    ),
)
def test_default_widget_no_count_links_for_ambiguous_columns(
    admin_client, dashboard_db, sql, should_have_count_links
):
    response = admin_client.post(
        "/dashboard/",
        {"sql": sql},
        follow=True,
    )
    soup = BeautifulSoup(response.content, "html5lib")
    th_links = soup.select("thead th a")
    if should_have_count_links:
        assert len(th_links)
    else:
        assert not len(th_links)


def test_big_number_widget(admin_client, dashboard_db):
    response = admin_client.post(
        "/dashboard/",
        {"sql": "select 'Big' as label, 10801 * 5 as big_number"},
        follow=True,
    )
    html = response.content.decode("utf-8")
    assert "<p>Big</p>\n  <h1>54005</h1>" in html


def test_markdown_widget(admin_client, dashboard_db):
    response = admin_client.post(
        "/dashboard/",
        {"sql": "select '# Foo\n\n## Bar [link](/)' as markdown"},
        follow=True,
    )
    html = response.content.decode("utf-8")
    assert '<h1>Foo</h1>\n<h2>Bar <a href="/" rel="nofollow">link</a></h2>' in html


def test_html_widget(admin_client, dashboard_db):
    response = admin_client.post(
        "/dashboard/",
        {
            "sql": "select '<h1>Hi</h1><script>alert(\"evil\")</script><p>There</p>' as markdown"
        },
        follow=True,
    )
    html = response.content.decode("utf-8")
    assert (
        "<h1>Hi</h1>\n" '&lt;script&gt;alert("evil")&lt;/script&gt;\n' "<p>There</p>"
    ) in html


def test_bar_chart_widget(admin_client, dashboard_db):
    sql = """
    SELECT * FROM (
        VALUES (1, 'one'), (2, 'two'), (3, 'three')
    ) AS t (bar_quantity, bar_label);
    """
    response = admin_client.post(
        "/dashboard/",
        {"sql": sql},
        follow=True,
    )
    html = response.content.decode("utf-8")
    assert (
        '<script id="vis-data-0" type="application/json">'
        '[{"bar_quantity": 1, "bar_label": "one"}, '
        '{"bar_quantity": 2, "bar_label": "two"}, '
        '{"bar_quantity": 3, "bar_label": "three"}]</script>'
    ) in html
    assert '$schema: "https://vega.github.io/schema/vega-lite/v5.json"' in html
