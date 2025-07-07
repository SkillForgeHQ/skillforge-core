import pytest
from unittest.mock import MagicMock

@pytest.fixture(autouse=True, scope="session")
def mock_neo4j_globally_session(session_mocker):
    """
    Session-scoped autouse fixture to mock Neo4jGraph.
    This ensures that when api.database.langchain_graph is defined at module import time,
    it uses a mocked Neo4jGraph, preventing actual DB connection attempts.
    `session_mocker` is provided by pytest-mock for session-scoped fixtures.
    """
from unittest.mock import patch, MagicMock

# Store the patcher object globally in conftest to stop it later
_neo4j_patcher = None
_openai_patcher = None # Declare _openai_patcher globally as well

@pytest.fixture(autouse=True, scope="session")
def mock_neo4j_globally_session_direct_unittest_mock(request):
    global _neo4j_patcher

    # Create a MagicMock that will act as the Neo4jGraph class
    # When Neo4jGraph() is called, it will call this mock, which in turn
    # returns another MagicMock (the instance). This bypasses original __init__.
    mock_neo4j_class = MagicMock()

    # Using new=mock_neo4j_class ensures that langchain_community.graphs.Neo4jGraph
    # is replaced by our mock_neo4j_class.
    _neo4j_patcher = patch("langchain_community.graphs.Neo4jGraph", new=mock_neo4j_class)
    _neo4j_patcher.start()

    # Mock ChatOpenAI as well to prevent it from trying to use a real API key
    mock_chat_openai_class = MagicMock()
    # If the llm object (instance of ChatOpenAI) is used, e.g. llm.invoke(),
    # this mock_chat_openai_class() will be called, returning a MagicMock instance.
    # That instance would then need its methods mocked if they are called.
    # For the current RAG chain definition, the llm object is part of the sequence,
    # but our test mocks out the whole rag_chain before the llm part is ever executed.
    # So, a simple MagicMock for the class should be enough to prevent init errors.
    # _openai_patcher = patch("langchain_openai.ChatOpenAI", new=mock_chat_openai_class) # Now handled by TESTING_MODE in app code
    # _openai_patcher.start()

    def fin():
        global _neo4j_patcher # _openai_patcher removed from global and from here
        if _neo4j_patcher:
            _neo4j_patcher.stop()
            _neo4j_patcher = None
        # if _openai_patcher: # Cleanup for _openai_patcher removed
        #     _openai_patcher.stop()
        #     _openai_patcher = None
    request.addfinalizer(fin)
