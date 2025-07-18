import uuid
import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.schemas import User
from api.ai.schemas import ParsedGoal, SubTask

client = TestClient(app)

@pytest.fixture
def mock_dependencies(mocker):
    # Mock graph db session
    mock_session = mocker.MagicMock(name="MOCK_SESSION")
    goal_node = {
        "id": uuid.uuid4(),
        "user_email": "user@example.com",
        "goal_text": "My Goal",
        "status": "in-progress",
        "full_plan_json": "[]",
    }
    quest_node = {
        "id": uuid.uuid4(),
        "name": "Step 1",
        "description": "Do something",
    }
    mock_session.write_transaction = mocker.MagicMock(return_value=(goal_node, quest_node))

    def override_get_graph_db_session():
        yield mock_session

    from api.main import app as main_app
    from api.database import get_graph_db_session as original_get_graph_db_session
    original_overrides = main_app.dependency_overrides.copy()
    main_app.dependency_overrides[original_get_graph_db_session] = override_get_graph_db_session

    # Mock current user
    def override_get_current_user():
        return User(id=1, email="user@example.com", is_active=True)
    from api.routers.auth import get_current_user as orig_get_current_user
    main_app.dependency_overrides[orig_get_current_user] = override_get_current_user

    yield

    main_app.dependency_overrides = original_overrides


def test_parse_goal_returns_goal_and_quest(mock_dependencies, mocker):
    sub_task = SubTask(title="Step 1", description="Do something", duration_minutes=10)
    parsed_goal = ParsedGoal(goal_title="My Goal", sub_tasks=[sub_task])

    class DummyChain:
        async def ainvoke(self, arg):
            return parsed_goal

    mocker.patch("api.routers.goals.goal_parser_chain", DummyChain())

    response = client.post("/goals/parse", json={"goal": "My Goal"})
    assert response.status_code == 200
    data = response.json()
    assert "goal" in data and "quest" in data
    assert data["goal"]["goal_text"] == "My Goal"
    assert data["quest"]["name"] == "Step 1"
