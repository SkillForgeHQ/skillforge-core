import pytest
import uuid
from api.graph_crud import create_quest, create_accomplishment, get_accomplishment_details
from api.schemas import Quest, AccomplishmentCreate

# Fixture for a mock Neo4j transaction
@pytest.fixture
def mock_tx(mocker):
    return mocker.MagicMock()

# Fixture for a mock Neo4j session
@pytest.fixture
def mock_session(mocker, mock_tx):
    session = mocker.MagicMock()
    session.write_transaction.side_effect = lambda func, *args, **kwargs: func(mock_tx, *args, **kwargs)
    session.read_transaction.side_effect = lambda func, *args, **kwargs: func(mock_tx, *args, **kwargs)
    return session

# Fixture for a mock graph_db_driver that returns the mock_session
@pytest.fixture
def mock_graph_db_driver(mocker, mock_session):
    driver = mocker.MagicMock()
    driver.session.return_value.__enter__.return_value = mock_session
    return driver

def test_create_quest(mock_tx):
    quest_data = {"name": "Test Quest", "description": "A quest for testing."}
    expected_quest_id = uuid.uuid4()
    mock_tx.run.return_value.single.return_value = {"q": {"id": expected_quest_id, **quest_data}}

    result = create_quest(mock_tx, quest_data)

    mock_tx.run.assert_called_once()
    args, kwargs = mock_tx.run.call_args # Get kwargs
    assert "CREATE (q:Quest)" in args[0]
    assert "SET q = $quest_data, q.id = randomUUID()" in args[0]
    assert kwargs["quest_data"] == quest_data # Check kwargs
    assert result["id"] == expected_quest_id
    assert result["name"] == quest_data["name"]

def test_create_accomplishment_without_quest(mock_tx):
    user_email = "test@example.com"
    accomplishment_data = {"name": "Test Accomplishment", "description": "Done something."}
    expected_accomplishment_id = uuid.uuid4()

    # Mock the return for creating the accomplishment
    mock_tx.run.return_value.single.return_value = {"a": {"id": expected_accomplishment_id, **accomplishment_data}}

    result = create_accomplishment(mock_tx, user_email, accomplishment_data)

    assert mock_tx.run.call_count == 1 # Only one call for accomplishment creation
    call_args_list = mock_tx.run.call_args_list

    # Check accomplishment creation call
    create_call_args, create_call_kwargs = call_args_list[0] # Get kwargs
    assert "MATCH (u:User {email: $user_email})" in create_call_args[0]
    assert "CREATE (a:Accomplishment)" in create_call_args[0]
    assert create_call_kwargs["user_email"] == user_email # Check kwargs
    assert create_call_kwargs["accomplishment_data"] == accomplishment_data # Check kwargs

    assert result["id"] == expected_accomplishment_id
    assert result["name"] == accomplishment_data["name"]

def test_create_accomplishment_with_quest(mock_tx, mocker): # Added mocker
    user_email = "test@example.com"
    accomplishment_data = {"name": "Test Accomplishment for Quest", "description": "Done something for a quest."}
    quest_id = str(uuid.uuid4())
    expected_accomplishment_id = uuid.uuid4()

    # Mock the return for creating the accomplishment (first call to tx.run)
    # Mock the return for linking to the quest (second call to tx.run)
    mock_tx.run.side_effect = [
        mocker.Mock(single=mocker.Mock(return_value={"a": {"id": expected_accomplishment_id, **accomplishment_data}})), # For CREATE Accomplishment
        mocker.Mock()  # For MERGE FULFILLS relationship
    ]

    result = create_accomplishment(mock_tx, user_email, accomplishment_data, quest_id=quest_id)

    assert mock_tx.run.call_count == 2 # Two calls: one for creation, one for linking
    call_args_list = mock_tx.run.call_args_list

    # Check accomplishment creation call
    create_call_args, create_call_kwargs = call_args_list[0] # Get kwargs
    assert "MATCH (u:User {email: $user_email})" in create_call_args[0]
    assert "CREATE (a:Accomplishment)" in create_call_args[0]
    assert create_call_kwargs["user_email"] == user_email # Check kwargs
    assert create_call_kwargs["accomplishment_data"] == accomplishment_data # Check kwargs

    # Check link to quest call
    link_call_args, link_call_kwargs = call_args_list[1] # Get kwargs
    assert "MATCH (a:Accomplishment {id: $accomplishment_id})" in link_call_args[0]
    assert "MATCH (q:Quest {id: $quest_id})" in link_call_args[0]
    assert "MERGE (a)-[:FULFILLS]->(q)" in link_call_args[0]
    assert link_call_kwargs["accomplishment_id"] == expected_accomplishment_id # Check kwargs
    assert link_call_kwargs["quest_id"] == quest_id # Check kwargs

    assert result["id"] == expected_accomplishment_id
    assert result["name"] == accomplishment_data["name"]
