import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, ANY
import uuid
from jose import jwt
from jwcrypto import jwk
import json
import datetime

# Assuming your FastAPI app instance is named 'app' in 'api.main'
# Adjust the import if your app instance is located elsewhere
from api.main import app
from api.schemas import Quest, AccomplishmentCreate, User
from api.routers.auth import get_current_user # To override dependency

client = TestClient(app)

# Mock user for dependency override
mock_user_email = "testuser@example.com"
MOCK_USER = User(id=1, email=mock_user_email, is_active=True)

async def override_get_current_user():
    return MOCK_USER

app.dependency_overrides[get_current_user] = override_get_current_user


from api.database import get_graph_db_driver # Import for dependency override

# --- Mocking Neo4j Driver and Session ---
@pytest.fixture(scope="function") # Changed to function scope, no longer autouse
def mock_neo4j_components(): # Renamed to avoid confusion, yields components
    mock_driver_instance = MagicMock(name="MockDriverInstance")
    mock_session_instance = MagicMock(name="MockSessionInstance")
    mock_tx_instance = MagicMock(name="MockTxInstance")

    mock_session_instance.write_transaction = MagicMock(name="MockSessionWriteTransaction")
    mock_session_instance.read_transaction = MagicMock(name="MockSessionReadTransaction")

    mock_driver_instance.session.return_value = mock_session_instance

    # This fixture now just provides the components. Override will be done in tests.
    yield mock_driver_instance, mock_session_instance, mock_tx_instance


@pytest.fixture(scope="function")
def client_with_mocked_db(mock_neo4j_components): # This fixture will set up the override
    mock_driver, _, _ = mock_neo4j_components # We only need the driver for the override lambda

    # Define a lambda that returns our mock_driver for the dependency
    override_get_driver = lambda: mock_driver

    # Apply the dependency override
    app.dependency_overrides[get_graph_db_driver] = override_get_driver

    yield client # Yield the global test client, now using the overridden app dependency

    # Clean up the override after the test
    del app.dependency_overrides[get_graph_db_driver]


# --- Tests for Goals Router (/goals/personalized-path) ---
def test_get_personalized_path_creates_quest(client_with_mocked_db, mock_neo4j_components):
    # client_with_mocked_db ensures app used by 'client' has the override
    # mock_neo4j_components provides access to the session and tx mocks
    _, mock_session, mock_tx = mock_neo4j_components

    goal_description = "Learn advanced Python programming"
    expected_quest_name = f"Personalized Quest for {mock_user_email}"
    expected_quest_description_fragment = goal_description # Part of the generated description

    # Mock the return value for graph_crud.create_quest (which is called inside the endpoint)
    # This is what tx.run(query, ...).single()['q'] would return
    mock_created_quest_node = {
        "id": str(uuid.uuid4()),
        "name": expected_quest_name,
        "description": f"Based on your goal '{goal_description}', a good first step would be to learn about its core concepts and create a small project. User: {mock_user_email}"
    }
    # Configure the mock transaction's run().single() behavior
    # The create_quest function in graph_crud.py expects tx.run(...).single() to return a dict like {'q': node_data}
    # This mock_tx.run setup is not strictly necessary for this test with the new strategy.
    # However, it doesn't hurt to keep it if other tests use mock_tx.
    mock_run_result = MagicMock()
    mock_run_result.single.return_value = {'q': mock_created_quest_node} # This is if create_quest was actually called with mock_tx
    # mock_tx.run.return_value = mock_run_result # Not directly used if we mock write_transaction's result/side_effect

    # Configure mock_session.write_transaction to return mock_created_quest_node when called.
    # Using side_effect to be very explicit about the call.
    def mock_write_transaction_side_effect(func, quest_data_arg, **kwargs):
        # We can assert here that func is graph_crud.create_quest if needed
        # and quest_data_arg is what we expect.
        # For this test, the key is to return the mock_created_quest_node.
        return mock_created_quest_node

    mock_session.write_transaction.side_effect = mock_write_transaction_side_effect

    response = client.post(
        "/goals/personalized-path",
        json={"goal_description": goal_description}
    )

    assert response.status_code == 200
    quest_response = response.json()
    assert quest_response["name"] == expected_quest_name
    assert expected_quest_description_fragment in quest_response["description"]
    assert quest_response["id"] == mock_created_quest_node["id"] # ID should now match

    # Assert that mock_session.write_transaction was called correctly
    from api import graph_crud # Import for referencing the function object
    mock_session.write_transaction.assert_called_once()
    call_args = mock_session.write_transaction.call_args

    # Check the function passed to write_transaction
    assert call_args[0][0] == graph_crud.create_quest

    # Check the quest_data dict passed to graph_crud.create_quest
    actual_quest_data = call_args[0][1]
    assert actual_quest_data["name"] == expected_quest_name
    assert expected_quest_description_fragment in actual_quest_data["description"]


# --- Tests for Accomplishments Router (/accomplishments/{accomplishment_id}/issue-credential) ---

# Mock private key for VC signing
MOCK_PRIVATE_KEY_JWK = {
    "kty": "EC",
    "crv": "P-256",
    "x": "ajhBzsb5UAuLANzuljVdMTqWrq-AMyrtWJDVgcnislo",
    "y": "Yxbzv8ruAR_AAB6cPY3-w3ZKHGhE8FhyRRQnKSGjvdE",
    "d": "N66GF1vBaLzbjYAHi7LxosrCGLC_o5uy4QUoxtUJt6w"
}
import io # Import io for StringIO

MOCK_PRIVATE_KEY_PEM = jwk.JWK(**MOCK_PRIVATE_KEY_JWK).export_to_pem(private_key=True, password=None)

@patch('builtins.open')
@patch('os.getenv')
def test_issue_accomplishment_credential_stores_receipt(mock_getenv, mock_open_builtin, client_with_mocked_db, mock_neo4j_components):
    # client_with_mocked_db ensures app used by 'client' has the override
    # mock_neo4j_components provides access to the session and tx mocks
    _, mock_session, mock_tx_graph = mock_neo4j_components # Use mock_neo4j_components

    # Setup mock environment variable and key file
    mock_getenv.return_value = "dummy_key_path.json"
    # Configure mock_open_builtin to return an StringIO object when called
    mock_open_builtin.return_value = io.StringIO(json.dumps(MOCK_PRIVATE_KEY_JWK))

    accomplishment_id = uuid.uuid4()

    # Mock data returned by graph_crud.get_accomplishment_details
    mock_accomplishment_details = {
        "user": {"email": mock_user_email},
        "accomplishment": {
            "id": str(accomplishment_id),
            "name": "Test Credential Accomplishment",
            "description": "Details for VC.",
            "timestamp": datetime.datetime.now(datetime.timezone.utc) # Neo4jDateTime will be converted
        }
    }

    # Configure the mock transaction for get_accomplishment_details
    # This function is called via read_transaction
    # We need to ensure the lambda func(mock_tx_graph, *args, **kwargs) correctly simulates its behavior
    # For get_accomplishment_details, it returns the dictionary directly.

    # To mock the behavior of tx.run().single() inside get_accomplishment_details:
    mock_run_result_fetch = MagicMock()
    mock_run_result_fetch.single.return_value = { # This is what record would be in get_accomplishment_details
        "u": mock_accomplishment_details["user"],
        "a": mock_accomplishment_details["accomplishment"]
    }
    # This configures the mock_tx_graph that will be passed into get_accomplishment_details
    # mock_tx_graph.run.return_value = mock_run_result_fetch # Not needed with new strategy

    # Configure mock_session.read_transaction to return the accomplishment details
    # This simulates graph_crud.get_accomplishment_details returning the data
    # The timestamp needs to be mockable to call .to_native().isoformat()
    mock_timestamp = MagicMock(name="MockTimestamp")
    mock_native_datetime = datetime.datetime.now(datetime.timezone.utc)
    mock_timestamp.to_native.return_value = mock_native_datetime

    mock_accomplishment_node_for_details = {
        "id": str(accomplishment_id),
        "name": "Test Credential Accomplishment",
        "description": "Details for VC.",
        "timestamp": mock_timestamp
    }
    mock_user_node_for_details = {"email": mock_user_email}

    # Define side_effect for read_transaction
    def mock_read_transaction_side_effect(func, acc_id_arg, **kwargs):
        # In this test, we expect it to be called to get accomplishment details
        # and it should return our mocked structure.
        return {
            "user": mock_user_node_for_details,
            "accomplishment": mock_accomplishment_node_for_details
        }
    mock_session.read_transaction.side_effect = mock_read_transaction_side_effect

    # mock_session.write_transaction is already a MagicMock. For this test, we can also use side_effect
    # if we need to inspect its arguments or control return, though store_vc_receipt doesn't return.
    # For now, default MagicMock behavior (returns a new mock if called) is fine for write_transaction here,
    # as the endpoint doesn't use its return value. We assert it's called later.

    response = client.post(f"/accomplishments/{str(accomplishment_id)}/issue-credential")

    assert response.status_code == 200
    assert "verifiable_credential_jwt" in response.json()

    from api import graph_crud # Import for referencing function objects

    # Verify that read_transaction was called for get_accomplishment_details
    mock_session.read_transaction.assert_called_once_with(
        graph_crud.get_accomplishment_details,
        accomplishment_id  # The endpoint passes the UUID object directly
    )

    # Verify that write_transaction was called for store_vc_receipt
    mock_session.write_transaction.assert_called_once()
    store_receipt_call_args = mock_session.write_transaction.call_args

    assert store_receipt_call_args[0][0] == graph_crud.store_vc_receipt
    assert store_receipt_call_args[0][1] == str(accomplishment_id) # store_vc_receipt gets str

    vc_receipt_arg = store_receipt_call_args[0][2]
    assert "id" in vc_receipt_arg
    assert "issuanceDate" in vc_receipt_arg

    # Verify the JWT structure (optional, more of a JWT library test)
    jwt_token = response.json()["verifiable_credential_jwt"]
    # Here you could decode and verify claims if needed, but that tests JWT logic more than the endpoint's new step
    # For this test, confirming store_vc_receipt was called is key.

@patch('builtins.open')
@patch('os.getenv')
def test_issue_credential_accomplishment_not_found(mock_getenv, mock_open_builtin, client_with_mocked_db, mock_neo4j_components):
    # client_with_mocked_db ensures app used by 'client' has the override
    # mock_neo4j_components provides access to the session and tx mocks
    _, mock_session, mock_tx_graph = mock_neo4j_components # Use mock_neo4j_components

    mock_getenv.return_value = "dummy_key_path.json"
    # Ensure mock_open_builtin is configured if 'open' is called in this test path
    # For this test, 'open' is called if get_accomplishment_details doesn't cause an early exit.
    # If accomplishment is not found, 'open' might not be reached.
    # However, to be safe, ensure it's configured like in the previous test if it could be called.
    mock_open_builtin.return_value = io.StringIO(json.dumps(MOCK_PRIVATE_KEY_JWK))
    accomplishment_id = uuid.uuid4()

    # Simulate get_accomplishment_details returning None (accomplishment not found)
    def mock_read_transaction_not_found_side_effect(func, acc_id_arg, **kwargs):
        return None
    mock_session.read_transaction.side_effect = mock_read_transaction_not_found_side_effect

    response = client.post(f"/accomplishments/{str(accomplishment_id)}/issue-credential")

    assert response.status_code == 404
    assert response.json()["detail"] == "Accomplishment not found."

    # Ensure store_vc_receipt was NOT called
    mock_session.write_transaction.assert_not_called()

# Cleanup dependency overrides after tests
def teardown_module(module):
    app.dependency_overrides = {}
