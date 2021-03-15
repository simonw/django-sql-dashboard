def test_big_number_widget(admin_client, dashboard_db):
    response = admin_client.post("/dashboard/", {
        "sql": "select 'Big' as label, 10801 * 5 as big_number"
    }, follow=True)
    assert b'<p>Big</p>\n  <h1>54,005</h1>' in response.content
