def test_staff_users_only(client):
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert response.url == "/admin/login/?next=/dashboard"


def test_staff_users_allowed(admin_client):
    response = admin_client.get("/dashboard")
    assert response.status_code == 200
    assert b"<title>Django SQL Dashboard</title>" in response.content
