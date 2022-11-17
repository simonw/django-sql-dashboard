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


def test_default_widget_pretty_prints_json(admin_client, dashboard_db):
    response = admin_client.post(
        "/dashboard/",
        {
            "sql": """
            select json_build_object('hello', json_build_array(1, 2, 3)) as json
            """
        },
        follow=True,
    )
    html = response.content.decode("utf-8")
    soup = BeautifulSoup(html, "html5lib")
    trs = soup.select("table tbody tr")
    assert str(trs[0].find("td")) == (
        '<td><pre class="json">{\n'
        '  "hello": [\n'
        "    1,\n"
        "    2,\n"
        "    3\n"
        "  ]\n"
        "}</pre></td>"
    )


@pytest.mark.parametrize(
    "sql,expected",
    (
        ("SELECT * FROM generate_series(0, 5)", "6 rows</p>"),
        ("SELECT 'hello'", "1 row</p>"),
        ("SELECT * FROM generate_series(0, 1000)", "Results were truncated"),
    ),
)
def test_default_widget_shows_row_count_or_truncated_message(
    admin_client, dashboard_db, sql, expected
):
    response = admin_client.post(
        "/dashboard/",
        {"sql": sql},
        follow=True,
    )
    assert expected in response.content.decode("utf-8")


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
    th = soup.select("thead th")[0]
    assert th["data-count-url"]
    querystring = th["data-count-url"].split("?")[1]
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
    ths_with_data_count_url = soup.select("th[data-count-url]")
    if should_have_count_links:
        assert len(ths_with_data_count_url)
    else:
        assert not len(ths_with_data_count_url)


def test_big_number_widget(admin_client, dashboard_db):
    response = admin_client.post(
        "/dashboard/",
        {"sql": "select 'Big' as label, 10801 * 5 as big_number"},
        follow=True,
    )
    html = response.content.decode("utf-8")
    assert (
        '    <div class="big-number">\n'
        "      <p><strong>Big</strong></p>\n"
        "      <h1>54005</h1>\n"
        "    </div>"
    ) in html


@pytest.mark.parametrize(
    "sql,expected",
    (
        (
            "select '# Foo\n\n## Bar [link](/)' as markdown",
            '<h1>Foo</h1>\n<h2>Bar <a href="/" rel="nofollow">link</a></h2>',
        ),
        ("select null as markdown", ""),
    ),
)
def test_markdown_widget(admin_client, dashboard_db, sql, expected):
    response = admin_client.post(
        "/dashboard/",
        {"sql": sql},
        follow=True,
    )
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert expected in html


def test_html_widget(admin_client, dashboard_db):
    response = admin_client.post(
        "/dashboard/",
        {
            "sql": "select '<h1>Hi</h1><script>alert(\"evil\")</script><p>There<br>And</p>' as markdown"
        },
        follow=True,
    )
    html = response.content.decode("utf-8")
    assert (
        "<h1>Hi</h1>\n"
        '&lt;script&gt;alert("evil")&lt;/script&gt;\n'
        "<p>There<br>And</p>"
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


def test_progress_bar_widget(admin_client, dashboard_db):
    response = admin_client.post(
        "/dashboard/",
        {"sql": "select 100 as total_count, 72 as completed_count"},
        follow=True,
    )
    html = response.content.decode("utf-8")
    assert "<h2>72 / 100: 72%</h2>" in html
    assert 'width: 72%">&nbsp;</div>' in html


def test_word_cloud_widget(admin_client, dashboard_db):
    sql = """
    select * from (
      values ('one', 1), ('two', 2), ('three', 3)
    ) as t (wordcloud_word, wordcloud_count);
    """
    response = admin_client.post(
        "/dashboard/",
        {"sql": sql},
        follow=True,
    )
    html = response.content.decode("utf-8")
    assert (
        '<script id="wordcloud-data-0" type="application/json">[{"wordcloud_word"'
        in html
    )
