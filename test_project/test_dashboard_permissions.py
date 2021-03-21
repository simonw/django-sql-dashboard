from enum import Enum

import pytest
from django.contrib.auth.models import Group, Permission

from django_sql_dashboard.models import Dashboard


def test_anonymous_users_denied(client):
    response = client.get("/dashboard/?sql=select+1")
    assert response.status_code == 302
    assert response.url == "/accounts/login/?next=/dashboard/%3Fsql%3Dselect%2B1"


def test_superusers_allowed(admin_client, dashboard_db):
    response = admin_client.get("/dashboard/")
    assert response.status_code == 200
    assert b"<title>Django SQL Dashboard</title>" in response.content


def test_must_have_execute_sql_permission(client, django_user_model, dashboard_db):
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
    assert client.get("/dashboard/").status_code == 302
    client.force_login(staff_no_permisssion)
    assert client.get("/dashboard/").status_code == 302
    client.force_login(staff_with_permission)
    assert client.get("/dashboard/").status_code == 200


def test_saved_dashboard_anonymous_users_denied_by_default(client, dashboard_db):
    dashboard = Dashboard.objects.create(slug="test")
    dashboard.queries.create(sql="select 11 + 34")
    response = client.get("/dashboard/test/")
    assert response.status_code == 403


class UserType(Enum):
    owner = 1
    anon = 2
    loggedin = 3
    groupmember = 4
    staff = 5
    superuser = 6


all_user_types = (
    UserType.owner,
    UserType.anon,
    UserType.loggedin,
    UserType.groupmember,
    UserType.staff,
    UserType.superuser,
)


@pytest.mark.parametrize(
    "view_policy,user_types_who_can_see,should_cache_control_private",
    (
        ("private", (UserType.owner,), True),
        ("public", all_user_types, False),
        ("unlisted", all_user_types, False),
        (
            "loggedin",
            (
                UserType.owner,
                UserType.loggedin,
                UserType.groupmember,
                UserType.staff,
                UserType.superuser,
            ),
            True,
        ),
        ("group", (UserType.owner, UserType.groupmember), True),
        ("staff", (UserType.owner, UserType.staff, UserType.superuser), True),
        ("superuser", (UserType.owner, UserType.superuser), True),
    ),
)
def test_saved_dashboard_view_permissions(
    client,
    dashboard_db,
    view_policy,
    user_types_who_can_see,
    django_user_model,
    should_cache_control_private,
):
    users = {
        UserType.owner: django_user_model.objects.create(username="owner"),
        UserType.anon: None,
        UserType.loggedin: django_user_model.objects.create(username="loggedin"),
        UserType.groupmember: django_user_model.objects.create(username="groupmember"),
        UserType.staff: django_user_model.objects.create(
            username="staff", is_staff=True
        ),
        UserType.superuser: django_user_model.objects.create(
            username="superuser", is_staff=True, is_superuser=True
        ),
    }
    group = Group.objects.create(name="view-group")
    users[UserType.groupmember].groups.add(group)
    dashboard = Dashboard.objects.create(
        slug="dash",
        owned_by=users[UserType.owner],
        view_policy=view_policy,
        view_group=group,
    )
    for user_type, user in users.items():
        if user is not None:
            client.force_login(user)
        else:
            client.logout()
        response = client.get("/dashboard/dash/")
        if user_type in user_types_who_can_see:
            assert response.status_code == 200
        else:
            assert response.status_code == 403
        if should_cache_control_private:
            assert response["cache-control"] == "private"
