def test_export_requires_setting(admin_client, dashboard_db):
    for key in ("export_csv_0", "export_tsv_0"):
        response = admin_client.post(
            "/dashboard/",
            {
                "sql": "SELECT 'hello' as label, * FROM generate_series(0, 10000)",
                key: "1",
            },
        )
        assert response.status_code == 403


def test_no_export_on_saved_dashboard(
    admin_client, dashboard_db, settings, saved_dashboard
):
    settings.DASHBOARD_ENABLE_FULL_EXPORT = True
    response = admin_client.get("/dashboard/test/")
    assert response.status_code == 200
    assert b'<pre class="sql">select 22 + 55</pre>' in response.content
    assert b"Export all as CSV" not in response.content


def test_export_csv(admin_client, dashboard_db, settings):
    settings.DASHBOARD_ENABLE_FULL_EXPORT = True
    response = admin_client.post(
        "/dashboard/",
        {
            "sql": "SELECT 'hello' as label, * FROM generate_series(0, 10000)",
            "export_csv_0": "1",
        },
    )
    body = b"".join(response.streaming_content)
    assert body.startswith(
        b"label,generate_series\r\nhello,0\r\nhello,1\r\nhello,2\r\n"
    )
    assert body.endswith(b"hello,9998\r\nhello,9999\r\nhello,10000\r\n")
    assert response["Content-Type"] == "text/csv"
    content_disposition = response["Content-Disposition"]
    assert content_disposition.startswith(
        'attachment; filename="select--hello--as-label'
    )
    assert content_disposition.endswith('.csv"')


def test_export_tsv(admin_client, dashboard_db, settings):
    settings.DASHBOARD_ENABLE_FULL_EXPORT = True
    response = admin_client.post(
        "/dashboard/",
        {
            "sql": "SELECT 'hello' as label, * FROM generate_series(0, 10000)",
            "export_tsv_0": "1",
        },
    )
    body = b"".join(response.streaming_content)
    assert body.startswith(
        b"label\tgenerate_series\r\nhello\t0\r\nhello\t1\r\nhello\t2\r\n"
    )
    assert body.endswith(b"hello\t9998\r\nhello\t9999\r\nhello\t10000\r\n")
    assert response["Content-Type"] == "text/tab-separated-values"
    content_disposition = response["Content-Disposition"]
    assert content_disposition.startswith(
        'attachment; filename="select--hello--as-label'
    )
    assert content_disposition.endswith('.tsv"')
