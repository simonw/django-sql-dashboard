from enum import Enum

import pytest
from bs4 import BeautifulSoup
from django.contrib.auth.models import Group, User

from django_sql_dashboard.models import Dashboard


def test_anonymous_user_redirected_to_login(client):
    response = client.get("/dashboard/?sql=select+1")
    assert response.status_code == 302
    assert response.url == "/admin/login/?next=/dashboard/%3Fsql%3Dselect%2B1"


def test_superusers_allowed(admin_client, dashboard_db):
    response = admin_client.get("/dashboard/")
    assert response.status_code == 200
    assert b"<title>SQL Dashboard</title>" in response.content


def test_must_have_execute_sql_permission(
    client, django_user_model, dashboard_db, execute_sql_permission
):
    not_staff = django_user_model.objects.create(username="not_staff")
    staff_no_permisssion = django_user_model.objects.create(
        username="staff_no_permission", is_staff=True
    )
    staff_with_permission = django_user_model.objects.create(
        username="staff_with_permission", is_staff=True
    )
    staff_with_permission.user_permissions.add(execute_sql_permission)
    assert staff_with_permission.has_perm("django_sql_dashboard.execute_sql")
    client.force_login(not_staff)
    assert client.get("/dashboard/").status_code == 403
    client.force_login(staff_no_permisssion)
    assert client.get("/dashboard/").status_code == 403
    client.force_login(staff_with_permission)
    assert client.get("/dashboard/").status_code == 200


def test_user_without_execute_sql_permission_does_not_see_count_links_on_saved_dashboard(
    client, django_user_model, execute_sql_permission, dashboard_db
):
    dashboard = Dashboard.objects.create(slug="test", view_policy="public")
    dashboard.queries.create(sql="select 11 + 34")
    user = django_user_model.objects.create(username="regular")
    client.force_login(user)
    response = client.get("/dashboard/test/")
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert "data-count-url=" not in html
    # If the user DOES have that permission they get the count links
    user.user_permissions.add(execute_sql_permission)
    response = client.get("/dashboard/test/")
    html = response.content.decode("utf-8")
    assert "data-count-url=" in html


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
    "view_policy,user_types_who_can_see",
    (
        ("private", (UserType.owner,)),
        ("public", all_user_types),
        ("unlisted", all_user_types),
        (
            "loggedin",
            (
                UserType.owner,
                UserType.loggedin,
                UserType.groupmember,
                UserType.staff,
                UserType.superuser,
            ),
        ),
        ("group", (UserType.owner, UserType.groupmember)),
        ("staff", (UserType.owner, UserType.staff, UserType.superuser)),
        ("superuser", (UserType.owner, UserType.superuser)),
    ),
)
def test_saved_dashboard_view_permissions(
    client,
    dashboard_db,
    view_policy,
    user_types_who_can_see,
    django_user_model,
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
    Dashboard.objects.create(
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
        if user is not None:
            assert response["cache-control"] == "private"


def test_unlisted_dashboard_has_meta_robots(client, dashboard_db):
    dashboard = Dashboard.objects.create(slug="unlisted", view_policy="unlisted")
    dashboard.queries.create(sql="select 11 + 34")
    response = client.get("/dashboard/unlisted/")
    assert response.status_code == 200
    assert b'<meta name="robots" content="noindex">' in response.content
    dashboard.view_policy = "public"
    dashboard.save()
    response2 = client.get("/dashboard/unlisted/")
    assert response2.status_code == 200
    assert b'<meta name="robots" content="noindex">' not in response2.content


@pytest.mark.parametrize(
    "dashboard,expected,expected_if_staff,expected_if_superuser",
    (
        ("owned_by_user", True, True, True),
        ("owned_by_other_private", False, False, False),
        ("owned_by_other_public", True, True, True),
        ("owned_by_other_unlisted", False, False, False),
        ("owned_by_other_loggedin", True, True, True),
        ("owned_by_other_group_not_member", False, False, False),
        ("owned_by_other_group_member", True, True, True),
        ("owned_by_other_staff", False, True, True),
        ("owned_by_other_superuser", False, False, True),
    ),
)
def test_get_visible_to_user(
    db, dashboard, expected, expected_if_staff, expected_if_superuser
):
    user = User.objects.create(username="test")
    other = User.objects.create(username="other")
    group_member = Group.objects.create(name="group_member")
    user.groups.add(group_member)
    group_not_member = Group.objects.create(name="group_not_member")
    Dashboard.objects.create(slug="owned_by_user", owned_by=user, view_policy="private")
    Dashboard.objects.create(
        slug="owned_by_other_private", owned_by=other, view_policy="private"
    )
    Dashboard.objects.create(
        slug="owned_by_other_public", owned_by=other, view_policy="public"
    )
    Dashboard.objects.create(
        slug="owned_by_other_unlisted", owned_by=other, view_policy="unlisted"
    )
    Dashboard.objects.create(
        slug="owned_by_other_loggedin", owned_by=other, view_policy="loggedin"
    )
    Dashboard.objects.create(
        slug="owned_by_other_group_not_member",
        owned_by=other,
        view_policy="group",
        view_group=group_not_member,
    )
    Dashboard.objects.create(
        slug="owned_by_other_group_member",
        owned_by=other,
        view_policy="group",
        view_group=group_member,
    )
    Dashboard.objects.create(
        slug="owned_by_other_staff", owned_by=other, view_policy="staff"
    )
    Dashboard.objects.create(
        slug="owned_by_other_superuser", owned_by=other, view_policy="superuser"
    )
    visible_dashboards = set(
        Dashboard.get_visible_to_user(user).values_list("slug", flat=True)
    )
    if expected:
        assert (
            dashboard in visible_dashboards
        ), "Expected user to be able to see {}".format(dashboard)
    else:
        assert (
            dashboard not in visible_dashboards
        ), "Expected user not to be able to see {}".format(dashboard)
    user.is_staff = True
    user.save()
    visible_dashboards = set(
        Dashboard.get_visible_to_user(user).values_list("slug", flat=True)
    )
    if expected_if_staff:
        assert (
            dashboard in visible_dashboards
        ), "Expected staff user to be able to see {}".format(dashboard)
    else:
        assert (
            dashboard not in visible_dashboards
        ), "Expected staff user not to be able to see {}".format(dashboard)
    user.is_superuser = True
    user.save()
    visible_dashboards = set(
        Dashboard.get_visible_to_user(user).values_list("slug", flat=True)
    )
    if expected_if_superuser:
        assert (
            dashboard in visible_dashboards
        ), "Expected super user to be able to see {}".format(dashboard)
    else:
        assert (
            dashboard not in visible_dashboards
        ), "Expected super user not to be able to see {}".format(dashboard)


def test_get_visible_to_user_no_dupes(db):
    owner = User.objects.create(username="owner", is_staff=True)
    group = Group.objects.create(name="group")
    for i in range(3):
        group.user_set.add(User.objects.create(username="user{}".format(i)))
    Dashboard.objects.create(
        owned_by=owner,
        slug="example",
        view_policy="public",
        view_group=group,
    )
    dashboards = list(
        Dashboard.get_visible_to_user(owner).values_list("slug", flat=True)
    )
    # This used to return ["example", "example", "example"]
    # Until I fixed https://github.com/simonw/django-sql-dashboard/issues/90
    assert dashboards == ["example"]


@pytest.mark.parametrize(
    "dashboard,expected,expected_if_staff,expected_if_superuser",
    (
        ("owned_by_user", True, True, True),
        ("owned_by_other_private", False, False, False),
        ("owned_by_other_loggedin", True, True, True),
        ("owned_by_other_group_not_member", False, False, False),
        ("owned_by_other_group_member", True, True, True),
        ("owned_by_other_staff", False, True, True),
        ("owned_by_other_superuser", False, False, True),
    ),
)
def test_user_can_edit(
    db, client, dashboard, expected, expected_if_staff, expected_if_superuser
):
    user = User.objects.create(username="test")
    other = User.objects.create(username="other")
    group_member = Group.objects.create(name="group_member")
    user.groups.add(group_member)
    group_not_member = Group.objects.create(name="group_not_member")
    Dashboard.objects.create(slug="owned_by_user", owned_by=user, edit_policy="private")
    Dashboard.objects.create(
        slug="owned_by_other_private", owned_by=other, edit_policy="private"
    )
    Dashboard.objects.create(
        slug="owned_by_other_loggedin", owned_by=other, edit_policy="loggedin"
    )
    Dashboard.objects.create(
        slug="owned_by_other_group_not_member",
        owned_by=other,
        edit_policy="group",
        edit_group=group_not_member,
    )
    Dashboard.objects.create(
        slug="owned_by_other_group_member",
        owned_by=other,
        edit_policy="group",
        edit_group=group_member,
    )
    Dashboard.objects.create(
        slug="owned_by_other_staff", owned_by=other, edit_policy="staff"
    )
    Dashboard.objects.create(
        slug="owned_by_other_superuser", owned_by=other, edit_policy="superuser"
    )
    dashboard_obj = Dashboard.objects.get(slug=dashboard)
    dashboard_obj.queries.create(sql="select 1 + 1")
    assert dashboard_obj.user_can_edit(user) == expected
    if dashboard != "owned_by_other_staff":
        # This test doesn't make sense for the 'staff' one, they cannot access admin
        # https://github.com/simonw/django-sql-dashboard/issues/44#issuecomment-835653787
        can_edit_using_admin = can_user_edit_using_admin(client, user, dashboard_obj)
        assert can_edit_using_admin == expected
        if can_edit_using_admin:
            # Check that they cannot edit the SQL queries, because they do not
            # have the execute_sql permisssion
            assert not user.has_perm("django_sql_dashboard.execute_sql")
            html = get_admin_change_form_html(client, user, dashboard_obj)
            soup = BeautifulSoup(html, "html5lib")
            assert soup.select("td.field-sql p")[0].text == "select 1 + 1"

    user.is_staff = True
    user.save()
    assert dashboard_obj.user_can_edit(user) == expected_if_staff
    assert can_user_edit_using_admin(client, user, dashboard_obj) == expected_if_staff

    # Confirm that staff user can see the correct dashboards listed
    client.force_login(user)
    dashboard_change_list_response = client.get(
        "/admin/django_sql_dashboard/dashboard/"
    )
    change_list_soup = BeautifulSoup(dashboard_change_list_response.content, "html5lib")
    visible_in_change_list = [
        a.text for a in change_list_soup.select("th.field-slug a")
    ]
    assert set(visible_in_change_list) == {
        "owned_by_other_staff",
        "owned_by_other_group_member",
        "owned_by_other_loggedin",
        "owned_by_user",
    }

    # Promote to superuser
    user.is_superuser = True
    user.save()
    assert dashboard_obj.user_can_edit(user) == expected_if_superuser
    assert can_user_edit_using_admin(client, user, dashboard_obj)


def get_admin_change_form_html(client, user, dashboard):
    # Only staff can access the admin:
    original_is_staff = user.is_staff
    user.is_staff = True
    user.save()
    client.force_login(user)
    response = client.get(dashboard.get_edit_url())
    if not original_is_staff:
        user.is_staff = False
        user.save()
    return response.content.decode("utf-8")


def can_user_edit_using_admin(client, user, dashboard):
    return (
        '<input type="text" name="title" class="vTextField" maxlength="128" id="id_title">'
        in get_admin_change_form_html(client, user, dashboard)
    )


def test_superuser_can_reassign_ownership(client, db):
    user = User.objects.create(username="test", is_staff=True)
    dashboard = Dashboard.objects.create(
        slug="dashboard", owned_by=user, view_policy="private", edit_policy="private"
    )
    client.force_login(user)
    response = client.get(dashboard.get_edit_url())
    assert (
        b'<div class="readonly">test</div>' in response.content
        or b'<div class="readonly"><a href="/admin/auth/user/' in response.content
    )
    assert b'<input type="text" name="owned_by" value="' not in response.content
    user.is_superuser = True
    user.save()
    response2 = client.get(dashboard.get_edit_url())
    assert b'<input type="text" name="owned_by" value="' in response2.content


def test_no_link_to_index_on_saved_dashboard_for_logged_out_user(client, db):
    dashboard = Dashboard.objects.create(
        slug="dashboard",
        owned_by=User.objects.create(username="test", is_staff=True),
        view_policy="public",
    )
    response = client.get(dashboard.get_absolute_url())
    assert b'<a href="/dashboard/">' not in response.content
