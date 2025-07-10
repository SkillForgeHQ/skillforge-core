# tests/test_db_connection.py
import os
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

def test_direct_db_connection():
    db_url = os.getenv("DATABASE_URL")
    assert db_url, "DATABASE_URL environment variable not set"
    print(f"Attempting direct connection with URL: {db_url}")

    try:
        engine = create_engine(db_url)
        connection = engine.connect()
        connection.close()
        print("Direct connection successful!")
        assert True
    except OperationalError as e:
        print(f"Direct connection failed: {e}")
        assert False, f"Failed to connect directly to the database: {e}"
