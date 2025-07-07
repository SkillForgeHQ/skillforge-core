# api/tests/test_qa.py
from fastapi.testclient import TestClient
from api.main import app
from api.routers.auth import create_access_token
from ..schemas import User
from datetime import timedelta

client = TestClient(app)


def get_test_user_token():
    """Helper function to get a valid token for a test user."""
    test_user = User(username="testuser", email="test@example.com", id=1)
    return create_access_token(
        data={"sub": test_user.username}, expires_delta=timedelta(minutes=15)
    )


def test_qa_endpoint_with_mocking(mocker):
    """
    Tests the /qa/ endpoint by mocking the RAG chain.
    The 'mocker' fixture is provided by pytest-mock.
    """
    # Arrange: Set up the test conditions
    token = get_test_user_token()
    headers = {"Authorization": f"Bearer {token}"}
    test_question = "What is Python?"
    mock_answer = "This is a predictable, mocked answer about Python."

    # Mock the RAG chain's `ainvoke` method
    # This tells pytest to replace the real call with a fake one
    mocker.patch(
        "api.routers.qa.rag_chain.ainvoke", return_value={"answer": mock_answer}
    )

    # Act: Call the API endpoint
    response = client.post("/qa/", headers=headers, json={"question": test_question})

    # Assert: Check if the outcome is what we expect
    assert response.status_code == 200
    assert response.json() == {"answer": mock_answer}
