from django_sql_dashboard.models import Dashboard


def test_save_dashboard(admin_client, dashboard_db):
    assert Dashboard.objects.count() == 0
    response = admin_client.post(
        "/dashboard/",
        {
            "sql": "select 1 + 1",
            "_save-slug": "one",
            "_save-view_policy": "private",
            "_save-edit_policy": "private",
        },
    )
    assert response.status_code == 302
    # Should redirect to new dashboard
    assert response.url == "/dashboard/one/"
    dashboard = Dashboard.objects.first()
    assert dashboard.slug == "one"
    assert list(dashboard.queries.values_list("sql", flat=True)) == ["select 1 + 1"]
