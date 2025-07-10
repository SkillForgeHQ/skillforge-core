import os
import pytest
from unittest.mock import patch, MagicMock
import json
from jwcrypto import jwk

print(f"DATABASE_URL_IN_CONFTEST: {os.getenv('DATABASE_URL')}")

# This global variable is used by the fixture to manage the patcher lifecycle.
_neo4j_constructor_patcher = None


def pytest_configure(config):
    """Sets TESTING_MODE=True and other default test environment variables very early."""
    os.environ["TESTING_MODE"] = "True"
    os.environ.setdefault(
        "DATABASE_URL", "postgresql://testuser:testpass@localhost:5432/testdb_ci"
    )
    os.environ.setdefault("NEO4J_URI", "neo4j://localhost:7687")
    os.environ.setdefault("NEO4J_USERNAME", "neo4j")
    os.environ.setdefault("NEO4J_PASSWORD", "password")
    os.environ.setdefault("OPENAI_API_KEY", "sk-testplaceholderkey_conftest")
    os.environ.setdefault("SECRET_KEY", "testsecretkey_conftest")
    os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")


@pytest.fixture(autouse=True, scope="session")
def mock_external_service_constructors(request):
    """
    Mocks constructors of external services like Neo4jGraph at a low level.
    """
    global _neo4j_constructor_patcher
    mock_neo4j_class = MagicMock(name="MockLangchainCommunityNeo4jGraphClass")
    _neo4j_constructor_patcher = patch(
        "langchain_community.graphs.Neo4jGraph", new=mock_neo4j_class
    )
    _neo4j_constructor_patcher.start()

    def fin():
        global _neo4j_constructor_patcher
        if _neo4j_constructor_patcher:
            _neo4j_constructor_patcher.stop()
            _neo4j_constructor_patcher = None

    request.addfinalizer(fin)


@pytest.fixture(scope="session")
def test_keys(tmp_path_factory):
    """
    Creates a temporary JWK key pair for the test session.
    """
    keys_path = tmp_path_factory.mktemp("keys")
    private_key_path = keys_path / "private_key.json"
    key = jwk.JWK.generate(kty="EC", crv="P-256")
    private_key_json = key.export_private()
    public_key_json = key.export_public()
    with open(private_key_path, "w") as f:
        f.write(private_key_json)
    return {
        "private_key_path": private_key_path,
        "public_key": jwk.JWK(**json.loads(public_key_json)),
        "issuer_id": "https://skillforge.io", # Align with hardcoded issuer in endpoint
    }


@pytest.fixture
def clean_db_client():
    """
    Provides a TestClient instance with a clean database state (PostgreSQL and Neo4j)
    by using an app factory and ensuring database tables are created and emptied.
    """
    # Removed erroneous import os and print statement from here
    from sqlalchemy import create_engine
    from fastapi.testclient import TestClient

    from api.main import create_app
    from api.database import metadata as pg_metadata, graph_db_manager, get_graph_db_driver

    DATABASE_URL_FOR_TESTS = os.getenv("DATABASE_URL")
    if not DATABASE_URL_FOR_TESTS:
        raise RuntimeError("DATABASE_URL not set for tests by pytest_configure.")

    test_setup_pg_engine = create_engine(DATABASE_URL_FOR_TESTS)

    pg_metadata.create_all(test_setup_pg_engine, checkfirst=True)
    with test_setup_pg_engine.connect() as connection:
        pg_tx = connection.begin()
        try:
            accomplishments_table = pg_metadata.tables.get("accomplishments")
            if accomplishments_table is not None:
                connection.execute(accomplishments_table.delete())
            users_table = pg_metadata.tables.get("users")
            if users_table is not None:
                connection.execute(users_table.delete())
            pg_tx.commit()
        except Exception as e:
            pg_tx.rollback()
            raise e
        finally:
            connection.close()

    if graph_db_manager.driver is not None:
        graph_db_manager.close()

    neo4j_driver_for_cleanup = get_graph_db_driver()
    with neo4j_driver_for_cleanup.session() as session:
        neo_tx = None
        try:
            neo_tx = session.begin_transaction()
            neo_tx.run("MATCH (n) DETACH DELETE n")
            neo_tx.commit()
        except Exception as e:
            if neo_tx:
                neo_tx.rollback()
            raise e

    app_instance = create_app()
    yield TestClient(app_instance)
