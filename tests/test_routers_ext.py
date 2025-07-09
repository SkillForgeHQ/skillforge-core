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


# --- Mocking Neo4j Driver and Session ---
@pytest.fixture(autouse=True)
def mock_neo4j_driver():
    with patch("api.database.get_graph_db_driver") as mock_get_driver:
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_tx = MagicMock() # Mock transaction object

        # Configure session to return the transaction mock
        mock_session.write_transaction.side_effect = lambda func, *args, **kwargs: func(mock_tx, *args, **kwargs)
        mock_session.read_transaction.side_effect = lambda func, *args, **kwargs: func(mock_tx, *args, **kwargs)

        mock_driver.session.return_value = mock_session
        mock_get_driver.return_value = mock_driver

        # Store tx on session to allow tests to configure its behavior (e.g., return_value for tx.run().single())
        mock_session.tx = mock_tx # Make tx accessible for configuration in tests
        yield mock_driver, mock_session, mock_tx


# --- Tests for Goals Router (/goals/personalized-path) ---
def test_get_personalized_path_creates_quest(mock_neo4j_driver):
    _, mock_session, mock_tx = mock_neo4j_driver

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
    mock_run_result = MagicMock()
    mock_run_result.single.return_value = {'q': mock_created_quest_node}
    mock_tx.run.return_value = mock_run_result

    response = client.post(
        "/goals/personalized-path",
        json={"goal_description": goal_description}
    )

    assert response.status_code == 200
    quest_response = response.json()
    assert quest_response["name"] == expected_quest_name
    assert expected_quest_description_fragment in quest_response["description"]
    assert "id" in quest_response

    # Verify that create_quest was called by the endpoint via session.write_transaction
    # The first argument to write_transaction is the function (graph_crud.create_quest)
    # The subsequent arguments are what's passed to that function
    # func_called = mock_session.write_transaction.call_args[0][0] # The function itself
    args_passed = mock_session.write_transaction.call_args[0] # All positional args to write_transaction

    # args_passed[0] is the transaction function (e.g., graph_crud.create_quest)
    # args_passed[1] is the first arg to that transaction function (e.g., quest_data)

    # Check that the create_quest function was indeed what write_transaction was told to execute
    assert mock_session.write_transaction.called
    # The first argument to write_transaction is the function to execute,
    # the second is the quest_data dict.
    actual_quest_data_arg = args_passed[1]
    assert actual_quest_data_arg["name"] == expected_quest_name
    assert actual_quest_data_arg["description"] is not None


# --- Tests for Accomplishments Router (/accomplishments/{accomplishment_id}/issue-credential) ---

# Mock private key for VC signing
MOCK_PRIVATE_KEY_JWK = {
    "kty": "EC",
    "crv": "P-256",
    "x": "test_x_val", # Replace with actual values if needed for jwcrypto
    "y": "test_y_val", # Replace with actual values if needed for jwcrypto
    "d": "test_d_val"  # Replace with actual values if needed for jwcrypto
}
MOCK_PRIVATE_KEY_PEM = jwk.JWK(**MOCK_PRIVATE_KEY_JWK).export_to_pem(private_key=True, password=None)

@patch('builtins.open', new_callable=MagicMock)
@patch('os.getenv')
def test_issue_accomplishment_credential_stores_receipt(mock_getenv, mock_open, mock_neo4j_driver):
    _, mock_session, mock_tx_graph = mock_neo4j_driver # Renamed mock_tx to mock_tx_graph to avoid clash

    # Setup mock environment variable and key file
    mock_getenv.return_value = "dummy_key_path.json"
    mock_open.return_value.read.return_value = json.dumps(MOCK_PRIVATE_KEY_JWK)

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
    mock_tx_graph.run.return_value = mock_run_result_fetch

    # Mock the transaction behavior for store_vc_receipt (called by write_transaction)
    # store_vc_receipt doesn't return anything, but we can check it was called.
    # The side_effect of write_transaction is already set up to call the function with mock_tx_graph.
    # So, graph_crud.store_vc_receipt(mock_tx_graph, ...) will be called.
    # We don't need a specific return mock for its tx.run() unless it affects subsequent logic.

    response = client.post(f"/accomplishments/{str(accomplishment_id)}/issue-credential")

    assert response.status_code == 200
    assert "verifiable_credential_jwt" in response.json()

    # Verify get_accomplishment_details was called
    # The read_transaction mock is configured to pass mock_tx_graph to the function it calls.
    # So, we check that mock_tx_graph.run was called with the query from get_accomplishment_details.
    # This is a bit indirect. A more direct way is to check mock_session.read_transaction.call_args
    # if we want to verify which function (e.g. graph_crud.get_accomplishment_details) was passed.

    # We expect two calls to tx.run(): one from get_accomplishment_details, one from store_vc_receipt
    # Let's check the call to store_vc_receipt via write_transaction
    assert mock_session.write_transaction.called

    # write_transaction_args[0] is the function (graph_crud.store_vc_receipt)
    # write_transaction_args[1] is accomplishment_id_str
    # write_transaction_args[2] is vc_receipt
    write_transaction_args = mock_session.write_transaction.call_args[0]

    called_func_for_write = write_transaction_args[0]
    # assert called_func_for_write.__name__ == "store_vc_receipt" # Check it's the right function

    passed_accomplishment_id_to_store = write_transaction_args[1]
    passed_vc_receipt = write_transaction_args[2]

    assert passed_accomplishment_id_to_store == str(accomplishment_id)
    assert "id" in passed_vc_receipt
    assert "issuanceDate" in passed_vc_receipt

    # Verify the JWT structure (optional, more of a JWT library test)
    jwt_token = response.json()["verifiable_credential_jwt"]
    # Here you could decode and verify claims if needed, but that tests JWT logic more than the endpoint's new step
    # For this test, confirming store_vc_receipt was called is key.

@patch('builtins.open', new_callable=MagicMock)
@patch('os.getenv')
def test_issue_credential_accomplishment_not_found(mock_getenv, mock_open, mock_neo4j_driver):
    _, mock_session, mock_tx_graph = mock_neo_driver # Corrected fixture name

    mock_getenv.return_value = "dummy_key_path.json"
    mock_open.return_value.read.return_value = json.dumps(MOCK_PRIVATE_KEY_JWK)
    accomplishment_id = uuid.uuid4()

    # Simulate get_accomplishment_details returning None (accomplishment not found)
    # This means tx.run().single() inside get_accomplishment_details would return None
    mock_run_result_fetch_notfound = MagicMock()
    mock_run_result_fetch_notfound.single.return_value = None # Simulate no record found
    mock_tx_graph.run.return_value = mock_run_result_fetch_notfound

    response = client.post(f"/accomplishments/{str(accomplishment_id)}/issue-credential")

    assert response.status_code == 404
    assert response.json()["detail"] == "Accomplishment not found."

    # Ensure store_vc_receipt was NOT called
    mock_session.write_transaction.assert_not_called()

# Fixture to correct typo in test_issue_credential_accomplishment_not_found
@pytest.fixture
def mock_neo_driver(mock_neo4j_driver):
    return mock_neo4j_driver

# Cleanup dependency overrides after tests
def teardown_module(module):
    app.dependency_overrides = {}
