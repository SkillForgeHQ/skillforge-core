import os
import pytest
from unittest.mock import patch, MagicMock
import json
from jwcrypto import jwk
import time
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from fastapi.testclient import TestClient

# --- Environment Configuration ---

def pytest_configure(config):
    """Sets default environment variables for the test suite."""
    os.environ["TESTING_MODE"] = "True"
    os.environ.setdefault(
        "DATABASE_URL", "postgresql://user:password@localhost:5432/skillforge_test"
    )
    os.environ.setdefault("NEO4J_URI", "neo4j://localhost:7687")
    os.environ.setdefault("NEO4J_USERNAME", "neo4j")
    os.environ.setdefault("NEO4J_PASSWORD", "password")
    os.environ.setdefault("OPENAI_API_KEY", "sk-testplaceholderkey_conftest")
    os.environ.setdefault("SECRET_KEY", "testsecretkey_conftest")
    os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")

# --- Mocks and Fixtures ---

@pytest.fixture(scope="session", autouse=True)
def mock_neo4j_graph_constructor():
    """Mocks the Langchain Neo4jGraph constructor for the entire session."""
    with patch("langchain_community.graphs.Neo4jGraph", MagicMock()) as mock:
        yield mock

@pytest.fixture(scope="session")
def test_keys(tmp_path_factory):
    """Creates a temporary JWK key pair for the test session."""
    keys_path = tmp_path_factory.mktemp("keys")
    private_key_path = keys_path / "private_key.json"
    key = jwk.JWK.generate(kty="EC", crv="P-256")
    with open(private_key_path, "w") as f:
        f.write(key.export_private())
    return {
        "private_key_path": private_key_path,
        "public_key": jwk.JWK(**json.loads(key.export_public())),
        "issuer_id": "https://skillforge.io",
    }

@pytest.fixture
def clean_db_client():
    """
    Provides a TestClient instance with a clean database state.

    **This fixture now includes a retry mechanism for the PostgreSQL connection
    to handle database startup delays in containerized environments.**
    """
    from api.main import create_app
    from api.database import metadata as pg_metadata, get_graph_db_driver

    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not set for tests.")

    # --- Resilient PostgreSQL Connection and Setup ---
    engine = create_engine(DATABASE_URL)
    max_retries = 10
    wait_seconds = 1
    for i in range(max_retries):
        try:
            # The first connection attempt happens here.
            with engine.connect() as connection:
                # Ensure tables exist before trying to delete from them
                pg_metadata.create_all(bind=engine, checkfirst=True)
                # Begin a transaction for cleanup
                with connection.begin():
                    # Iterate over tables in reverse order of creation for safe deletion
                    for table in reversed(pg_metadata.sorted_tables):
                         connection.execute(table.delete())
            print(f"✅ PostgreSQL connection successful and tables cleaned after {i + 1} attempts.")
            break
        except OperationalError as e:
            if "Connection refused" in str(e) and i < max_retries - 1:
                print(f"PostgreSQL connection refused. Retrying in {wait_seconds}s... ({i+1}/{max_retries})")
                time.sleep(wait_seconds)
            else:
                # If it's not a "Connection refused" error, or if max_retries is reached, re-raise.
                raise RuntimeError(f"Could not connect to PostgreSQL after {i+1} attempts or other OperationalError occurred.") from e
        except Exception as e: # Catch other potential exceptions during cleanup
            print(f"An unexpected error occurred during PostgreSQL cleanup: {e}")
            # Depending on the severity, you might want to re-raise or handle differently
            raise

    # --- Neo4j Cleanup ---
    # Assuming get_graph_db_driver() correctly returns a Neo4j driver instance
    # and handles its own connection pooling/management.
    neo4j_driver = get_graph_db_driver()
    try:
        with neo4j_driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        print("✅ Neo4j cleanup successful.")
    except Exception as e:
        print(f"An error occurred during Neo4j cleanup: {e}")
        # Depending on the severity, you might want to re-raise or handle
        raise


    # --- App and Client Creation ---
    app_instance = create_app()
    yield TestClient(app_instance)
