import pytest
from fastapi.testclient import TestClient
from api.main import app # Assuming your FastAPI app instance is named 'app'
from api.schemas import Quest as QuestSchema # Import the Pydantic model
import uuid

client = TestClient(app)

@pytest.fixture
def mock_graph_db_session_for_quests(mocker):
    the_mock_session = mocker.MagicMock(name="THE_MOCK_SESSION_INSTANCE")

    default_side_effect = lambda func, data_dict: {
        "id": uuid.uuid4(),
        "name": data_dict["name"],
        "description": data_dict["description"]
    }
    the_mock_session.write_transaction = mocker.MagicMock(
        name="MOCK_WRITE_TRANSACTION",
        side_effect=default_side_effect
    )

    # This function will be the override for get_graph_db_session
    def override_get_graph_db_session():
        yield the_mock_session

    # Import app and the original dependency for overriding
    from api.main import app as main_app # renamed to avoid conflict if client uses 'app'
    from api.database import get_graph_db_session as original_get_graph_db_session

    # Store original overrides if any, to restore them
    original_overrides = main_app.dependency_overrides.copy()
    main_app.dependency_overrides[original_get_graph_db_session] = override_get_graph_db_session

    yield the_mock_session # Yield the mock session for the test to use

    # Clean up the override after the test by restoring original state
    main_app.dependency_overrides = original_overrides


def test_create_quest_endpoint(mock_graph_db_session_for_quests, mocker):
    quest_create_data = {"name": "API Test Quest", "description": "Testing the quest creation endpoint."}

    # If your endpoint uses a Pydantic model for request that's different from QuestSchema (e.g. QuestCreate)
    # ensure quest_create_data matches that. Here, we assume QuestCreate has name and description.

    from api.main import app as main_app
    client = TestClient(main_app)
    response = client.post("/quests/", json=quest_create_data)

    assert response.status_code == 200
    response_data = response.json()

    assert response_data["name"] == quest_create_data["name"]
    assert response_data["description"] == quest_create_data["description"]
    assert "id" in response_data
    try:
        uuid.UUID(response_data["id"]) # Check if id is a valid UUID
    except ValueError:
        pytest.fail("ID is not a valid UUID")

    # Assert that the mock session's write_transaction was called correctly
    mock_graph_db_session_for_quests.write_transaction.assert_called_once()
    args, kwargs = mock_graph_db_session_for_quests.write_transaction.call_args
    # args[0] is the function (db_create_quest), args[1] is quest_data
    assert args[1]["name"] == quest_create_data["name"]
    assert args[1]["description"] == quest_create_data["description"]


def test_create_quest_endpoint_creation_fails(mock_graph_db_session_for_quests, mocker):
    # Simulate the DB operation returning None (e.g., creation failed)
    # Now mock_graph_db_session_for_quests refers to the session mock itself.
    # Its write_transaction attribute is already a MagicMock.
    mock_graph_db_session_for_quests.write_transaction.side_effect = None # Clear any default side_effect
    mock_graph_db_session_for_quests.write_transaction.return_value = None # Set specific return for this test

    quest_create_data = {"name": "Fail Quest", "description": "This should fail."}

    response = client.post("/quests/", json=quest_create_data)

    assert response.status_code == 400
    assert response.json() == {"detail": "Quest could not be created"}

    # write_transaction is called with (function_to_execute, data_for_function)
    # The first argument to write_transaction is the actual graph_crud.create_quest function
    # The second argument is the quest_data dictionary
    mock_graph_db_session_for_quests.write_transaction.assert_called_once()
    args, _kwargs = mock_graph_db_session_for_quests.write_transaction.call_args
    assert args[1] == quest_create_data # args[0] is the function, args[1] is the data
    # It is also possible to check the function itself if needed:
    # from api.graph_crud import create_quest as db_create_quest
    # assert args[0] == db_create_quest
