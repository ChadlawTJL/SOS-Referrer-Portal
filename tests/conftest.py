import pytest

from App import app as flask_app


@pytest.fixture
def app():
    flask_app.config.update(
        TESTING=True,
        SECRET_KEY="test-only-secret"
    )

    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def logged_in_user(client):
    """Creates a fake logged-in standard user session."""

    with client.session_transaction() as session:
        session["user_id"] = 999
        session["is_admin"] = False
        session["organisation_id"] = 999

    return client


@pytest.fixture
def logged_in_admin(client):
    """Creates a fake logged-in administrator session."""

    with client.session_transaction() as session:
        session["user_id"] = 998
        session["is_admin"] = True
        session["organisation_id"] = 999

    return client