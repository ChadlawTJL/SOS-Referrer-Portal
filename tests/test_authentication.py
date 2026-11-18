#test login authetication
def test_dashboard_requires_login(client):

    response = client.get("/")

    assert response.status_code == 302
    #if user isnt logged in, get redirected to login
    assert "/login" in response.headers["Location"]


def test_dashboard_access_when_logged_in(logged_in_user):

    response = logged_in_user.get("/")

    assert response.status_code == 200