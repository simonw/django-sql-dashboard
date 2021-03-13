from django.contrib.auth.models import Permission


def test_anonymous_users_denied(client):
    response = client.get("/dashboard?sql=select+1")
    assert response.status_code == 302
    assert response.url == "/accounts/login/?next=/dashboard%3Fsql%3Dselect%2B1"


def test_superusers_allowed(admin_client):
    response = admin_client.get("/dashboard")
    assert response.status_code == 200
    assert b"<title>Django SQL Dashboard</title>" in response.content


def test_must_have_execute_sql_permission(client, django_user_model):
    execute_sql = Permission.objects.get(
        content_type__app_label="django_sql_dashboard",
        content_type__model="dashboard",
        codename="execute_sql",
    )
    not_staff = django_user_model.objects.create(username="not_staff")
    staff_no_permisssion = django_user_model.objects.create(
        username="staff_no_permission", is_staff=True
    )
    staff_with_permission = django_user_model.objects.create(
        username="staff_with_permission", is_staff=True
    )
    staff_with_permission.user_permissions.add(execute_sql)
    assert staff_with_permission.has_perm("django_sql_dashboard.execute_sql")
    client.force_login(not_staff)
    assert client.get("/dashboard").status_code == 302
    client.force_login(staff_no_permisssion)
    assert client.get("/dashboard").status_code == 302
    client.force_login(staff_with_permission)
    assert client.get("/dashboard").status_code == 200
