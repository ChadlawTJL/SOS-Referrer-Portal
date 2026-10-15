from database import get_db_connection


def test_database_connection():
    conn = get_db_connection()

    assert conn is not None

    conn.close()