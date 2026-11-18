def test_admin_requires_login(client):

    response = client.get("/admin")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_standard_user_cannot_access_admin(logged_in_user):

    response = logged_in_user.get("/admin")
#302 is a redirect - so route exists but user doesnt have access
    assert response.status_code == 302


def test_admin_session_identified_as_admin(logged_in_admin):

    with logged_in_admin.session_transaction() as session:

        assert session["is_admin"] is True