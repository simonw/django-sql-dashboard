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
