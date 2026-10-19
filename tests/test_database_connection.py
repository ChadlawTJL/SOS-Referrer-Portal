from database import get_db_connection

#testing database connection, 
def test_database_connection():
    conn = get_db_connection()

    assert conn is not None


    conn.close()