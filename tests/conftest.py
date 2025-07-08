import os
import pytest
from unittest.mock import patch, MagicMock
import json
from jwcrypto import jwk

# This global variable is used by the fixture to manage the patcher lifecycle.
_neo4j_constructor_patcher = None


def pytest_configure(config):
    """Sets TESTING_MODE=True and other default test environment variables very early."""
    os.environ["TESTING_MODE"] = "True"
    # Set default values for other environment variables if they are not already set.
    # This is useful for CI environments where a .env file might not be present or sourced.
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
    This acts as a safety net in case the TESTING_MODE environment variable
    isn't effective in preventing their instantiation in all contexts during import.
    """
    global _neo4j_constructor_patcher

    # Mock the Neo4jGraph class from langchain_community.graphs
    # When Neo4jGraph(...) is called, it will use this MagicMock class.
    # Instantiating this MagicMock class (e.g. Neo4jGraph()) will return another MagicMock (the instance).
    # This prevents the original __init__ (which tries to connect) from running.
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
    # Create a temporary directory for the keys
    keys_path = tmp_path_factory.mktemp("keys")
    private_key_path = keys_path / "private_key.json"

    # Generate a key
    key = jwk.JWK.generate(kty="EC", crv="P-256")
    private_key_json = key.export_private()
    public_key_json = key.export_public()

    # Save the private key to the temporary file
    with open(private_key_path, "w") as f:
        f.write(private_key_json)

    # Return the path to the private key and the public key object
    return {
        "private_key_path": private_key_path,
        "public_key": jwk.JWK(**json.loads(public_key_json)),
        "issuer_id": "https://skillforge.test",  # Use a test issuer
    }


# Note:
# Mocking for ChatOpenAI and the RAG chain instance (api.ai.qa_service.rag_chain)
# is now handled by the TESTING_MODE checks directly within the application code
# (api/ai/qa_service.py), where they are replaced by MagicMock instances.
# The api.database.langchain_graph is also handled by TESTING_MODE in api/database.py.
# This conftest.py primarily ensures TESTING_MODE is set early and provides a
# fallback mock for the Neo4jGraph class constructor itself if it were ever reached.
