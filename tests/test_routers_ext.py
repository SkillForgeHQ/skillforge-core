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

    # Verify that create_quest was called by the endpoint.
    # The mock_session.write_transaction has a side_effect that calls the graph_crud function with mock_tx.
    # So we check that mock_tx.run was called, which is the actual Neo4j operation.
    mock_tx.run.assert_called_once()

    # Inspect the arguments passed to mock_tx.run
    # run_args[0] is a tuple of positional arguments (query_string,)
    # run_args[1] is a dictionary of keyword arguments (params_for_query)
    run_call_args = mock_tx.run.call_args

    # Ensure the query for creating a quest was executed
    actual_query_string = run_call_args[0][0]
    assert "CREATE (q:Quest {id: $id, name: $name, description: $description})" in actual_query_string

    # Check that the parameters passed to the Cypher query are correct
    passed_cypher_params = run_call_args[1]
    assert passed_cypher_params["name"] == expected_quest_name
    assert expected_quest_description_fragment in passed_cypher_params["description"]
    assert "id" in passed_cypher_params # create_quest generates an ID


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

@patch('builtins.open') # Removed new_callable, will assign side_effect
@patch('os.getenv')
def test_issue_accomplishment_credential_stores_receipt(mock_getenv, mock_open_builtin, mock_neo4j_driver): # Renamed mock_open to mock_open_builtin
    _, mock_session, mock_tx_graph = mock_neo4j_driver

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
    mock_tx_graph.run.return_value = mock_run_result_fetch

    # Mock the transaction behavior for store_vc_receipt (called by write_transaction)
    # store_vc_receipt doesn't return anything, but we can check it was called.
    # The side_effect of write_transaction is already set up to call the function with mock_tx_graph.
    # So, graph_crud.store_vc_receipt(mock_tx_graph, ...) will be called.
    # We don't need a specific return mock for its tx.run() unless it affects subsequent logic.

    # Ensure the mock for get_accomplishment_details is active when the endpoint calls it
    # The read_transaction side_effect calls get_accomplishment_details with mock_tx_graph
    # So, mock_tx_graph.run should be called by get_accomplishment_details

    response = client.post(f"/accomplishments/{str(accomplishment_id)}/issue-credential")

    # Check if get_accomplishment_details query was run
    # This confirms that the read_transaction part of the endpoint was hit and used our mock_tx_graph
    get_details_query_found = False
    for call_args in mock_tx_graph.run.call_args_list:
        query_string = call_args[0][0] # First positional argument is the query
        if "MATCH (u:User)-[:COMPLETED]->(a:Accomplishment {id: $accomplishment_id})" in query_string:
            get_details_query_found = True
            # Optionally, check parameters if needed:
            # called_params = call_args[1]
            # assert called_params['accomplishment_id'] == str(accomplishment_id)
            break
    assert get_details_query_found, "The query from get_accomplishment_details was not run on mock_tx_graph."

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

@patch('builtins.open')
@patch('os.getenv')
def test_issue_credential_accomplishment_not_found(mock_getenv, mock_open_builtin, mock_neo4j_driver):
    _, mock_session, mock_tx_graph = mock_neo4j_driver

    mock_getenv.return_value = "dummy_key_path.json"
    # Ensure mock_open_builtin is configured if 'open' is called in this test path
    # For this test, 'open' is called if get_accomplishment_details doesn't cause an early exit.
    # If accomplishment is not found, 'open' might not be reached.
    # However, to be safe, ensure it's configured like in the previous test if it could be called.
    mock_open_builtin.return_value = io.StringIO(json.dumps(MOCK_PRIVATE_KEY_JWK))
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

# Cleanup dependency overrides after tests
def teardown_module(module):
    app.dependency_overrides = {}
