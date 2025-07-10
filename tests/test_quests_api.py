import pytest
from fastapi.testclient import TestClient
from api.main import app # Assuming your FastAPI app instance is named 'app'
from api.schemas import Quest as QuestSchema # Import the Pydantic model
import uuid

client = TestClient(app)

@pytest.fixture
def mock_graph_db_session_for_quests(mocker):
    mock_session = mocker.MagicMock()

    def mock_write_transaction(func, quest_data_dict):
        # Simulate quest creation in DB
        created_quest_data = {
            "id": uuid.uuid4(),
            "name": quest_data_dict["name"],
            "description": quest_data_dict["description"]
        }
        return created_quest_data

    mock_session.write_transaction = mock_write_transaction

    # Mock the get_graph_db_session dependency
    # This requires knowing how get_graph_db_session is structured.
    # If it's a context manager:
    mock_db_conn_manager = mocker.patch("api.routers.quests.get_graph_db_session")
    mock_db_conn_manager.return_value.__enter__.return_value = mock_session
    return mock_session


def test_create_quest_endpoint(mock_graph_db_session_for_quests, mocker):
    quest_create_data = {"name": "API Test Quest", "description": "Testing the quest creation endpoint."}

    # If your endpoint uses a Pydantic model for request that's different from QuestSchema (e.g. QuestCreate)
    # ensure quest_create_data matches that. Here, we assume QuestCreate has name and description.

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
    mock_graph_db_session_for_quests.write_transaction.return_value = None

    quest_create_data = {"name": "Fail Quest", "description": "This should fail."}

    response = client.post("/quests/", json=quest_create_data)

    assert response.status_code == 400
    assert response.json() == {"detail": "Quest could not be created"}

    mock_graph_db_session_for_quests.write_transaction.assert_called_once_with(
        mocker.ANY, # The first argument is the create_quest function from graph_crud
        quest_create_data
    )
