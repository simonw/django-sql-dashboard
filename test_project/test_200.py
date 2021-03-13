def test_200(client):
    response = client.get("/200")
    assert response.status_code == 200
    assert response.content == b"Status 200"
