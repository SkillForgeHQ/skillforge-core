# conftest.py

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
    """
    Forcefully sets the correct environment variables for the entire test session.
    This overrides any variables from the CI runner, ensuring consistency.
    """
    os.environ["TESTING_MODE"] = "True"
    os.environ["DATABASE_URL"] = "postgresql://testuser:testpassword@localhost:5432/skillforge_test"
    os.environ["NEO4J_URI"] = "neo4j://localhost:7687"
    os.environ["NEO4J_USERNAME"] = "neo4j"
    os.environ["NEO4J_PASSWORD"] = "testpassword"
    os.environ["OPENAI_API_KEY"] = "sk-testplaceholderkey"
    os.environ["SECRET_KEY"] = "testsecretkey"
    os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"


# --- Mocks and Fixtures ---

@pytest.fixture(scope="session", autouse=True)
def mock_neo4j_graph_constructor():
    """Mocks the Langchain Neo4jGraph constructor for the entire session."""
    # Ensure langchain_community.graphs is the correct path
    # If api.database directly imports Neo4jGraph, that specific import needs patching.
    # Assuming it's used as langchain_community.graphs.Neo4jGraph somewhere.
    # If the direct import is `from langchain_community.graphs import Neo4jGraph` in `api.database`,
    # then the patch target should be `api.database.Neo4jGraph`.
    # Let's try patching the most likely direct usage if it's not already working.
    # For now, keeping the provided patch target.
    with patch("langchain_community.graphs.Neo4jGraph", MagicMock()):
        yield


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
    Provides a TestClient instance with a clean database state,
    with a retry mechanism for the database connection.
    """
    from api.main import create_app
    # api.database is where get_graph_db_driver and pg_metadata are.
    # It will be loaded after pytest_configure has set the env vars.
    from api.database import metadata as pg_metadata, get_graph_db_driver

    DATABASE_URL = os.getenv("DATABASE_URL") # Should pick up value from pytest_configure
    engine = create_engine(DATABASE_URL)

    # Retry loop to wait for the database service to be ready
    for i in range(10):
        try:
            with engine.connect() as connection:
                print("✅ PostgreSQL connection successful.")
                # Clear tables before test
                for table in reversed(pg_metadata.sorted_tables):
                    connection.execute(table.delete())
                connection.commit() # Ensure changes are committed
            break
        except OperationalError as e:
            if i < 9:
                print(f"PostgreSQL connection failed. Retrying in 1s... ({i+1}/10)")
                time.sleep(1)
            else:
                print(f"Final PostgreSQL connection attempt failed: {e}")
                raise e

    # Clear Neo4j
    neo4j_driver = None
    try:
        neo4j_driver = get_graph_db_driver() # This will use env vars set by pytest_configure
        with neo4j_driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("✅ Neo4j cleanup successful.")
    except Exception as e:
        print(f"Neo4j cleanup failed: {e}")
        # This could be made fatal if Neo4j must be clean for tests
        # For now, just printing the error.
    finally:
        if neo4j_driver:
            neo4j_driver.close()


    app_instance = create_app() # create_app should ideally use the env vars
    yield TestClient(app_instance)
