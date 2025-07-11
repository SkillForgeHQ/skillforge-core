import pytest
import uuid
from jose import jwt
from unittest.mock import patch, AsyncMock, MagicMock

# Import the specific dependency to be overridden
from api.routers.auth import get_current_user
from api.schemas import User # User is correctly in api.schemas
from api.ai.schemas import ExtractedSkills, SkillLevel, SkillMatch # AI schemas are in api.ai.schemas
from api import graph_crud # Ensure graph_crud is imported if used by spy

# NOTE: The TestClient is now provided by the `clean_db_client` fixture.
# No global `app` or `client` is needed here.

def test_issue_vc_for_accomplishment(monkeypatch, test_keys, clean_db_client):
    client = clean_db_client

    # Mock file open for private key
    original_open = open
    def mock_open(file, *args, **kwargs):
        if file == "private_key.json":
            return original_open(test_keys["private_key_path"], *args, **kwargs)
        return original_open(file, *args, **kwargs)
    monkeypatch.setattr("builtins.open", mock_open)

    # Mock AI services
    mock_chain_instance = MagicMock()
    mock_chain_instance.ainvoke = AsyncMock(return_value=ExtractedSkills(skills=[])) # Return empty skills for simplicity
    monkeypatch.setattr("api.routers.accomplishments.skill_extractor_chain", mock_chain_instance)

    # Mock find_skill_match as well, as it's called after skill extraction
    async def mock_find_skill_match_vc(candidate_skill_name, existing_skill_names):
        return SkillMatch(is_duplicate=False, existing_skill_name=None)
    monkeypatch.setattr("api.routers.accomplishments.find_skill_match", mock_find_skill_match_vc)


    # 1. Create User and Log In
    user_email = f"test.vc.user.{uuid.uuid4().hex[:6]}@skillforge.io"
    user_payload = {"email": user_email, "name": "VC Test User", "password": "password"}
    user_creation_response = client.post("/users/", json=user_payload)
    assert user_creation_response.status_code == 201, user_creation_response.text

    token_response = client.post("/token", data={"username": user_email, "password": "password"})
    assert token_response.status_code == 200, token_response.text
    auth_headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}

    # 2. Process Accomplishment
    accomplishment_payload = {"name": "Built a Test Case", "description": "A test case."}
    # The endpoint was changed from /accomplishments/process to /process
    response = client.post("/accomplishments/process", json=accomplishment_payload, headers=auth_headers)
    assert response.status_code == 200, response.text
    accomplishment_id = response.json()["accomplishment"]["id"]

    # 3. Issue VC
    # The endpoint was changed from /accomplishments/{accomplishment_id}/issue-credential to /{accomplishment_id}/issue-credential
    vc_response = client.post(f"/accomplishments/{accomplishment_id}/issue-credential", headers=auth_headers)
    assert vc_response.status_code == 200, vc_response.text
    signed_vc_jwt = vc_response.json()["verifiable_credential_jwt"]

    # 4. Verify VC
    public_pem = test_keys["public_key"].export_to_pem()
    decoded_token = jwt.decode(signed_vc_jwt, public_pem, algorithms=["ES256"], issuer=test_keys["issuer_id"])
    assert decoded_token["iss"] == test_keys["issuer_id"]
    assert decoded_token["vc"]["credentialSubject"]["accomplishment"]["name"] == "Built a Test Case"


def test_process_accomplishment_with_quest_id(monkeypatch, clean_db_client):
    client = clean_db_client

    # Mock AI services
    mock_chain = MagicMock()
    mock_chain.ainvoke = AsyncMock(return_value=ExtractedSkills(skills=[SkillLevel(skill="Testing", level="Advanced")]))
    monkeypatch.setattr("api.routers.accomplishments.skill_extractor_chain", mock_chain)

    async def mock_find_skill(c, e): return SkillMatch(is_duplicate=False, existing_skill_name=None) # Ensure existing_skill_name for new skill
    monkeypatch.setattr("api.routers.accomplishments.find_skill_match", mock_find_skill)

    # 1. Create User and Log In
    user_email = f"test.quest.user.{uuid.uuid4().hex[:6]}@skillforge.io"
    user_payload = {"email": user_email, "name": "Quest Test User", "password": "password"}
    user_creation_response = client.post("/users/", json=user_payload)
    assert user_creation_response.status_code == 201, user_creation_response.text

    token_response = client.post("/token", data={"username": user_email, "password": "password"})
    assert token_response.status_code == 200, token_response.text
    auth_headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}

    # 2. Create Quest
    # Assuming /goals/parse is the correct endpoint for creating a quest and returns its ID.
    # This part might need adjustment based on actual quest creation logic.
    # For this test, we mainly care that a valid quest_id (UUID string) is obtained.
    # Let's mock a simple quest creation if /goals/parse is too complex or not the direct way.
    # For now, let's assume a quest can be created and its ID retrieved.
    # If /goals/parse is not suitable, this should be a direct /quests/ POST if available.
    # The user's new code uses /goals/parse, so we stick to that.
    quest_create_payload = {"goal": "Test a quest-linked accomplishment"} # Payload for /goals/parse
    # The /goals/parse endpoint might require auth, add headers if so.
    # Based on the user's snippet, it seems it might.
    quests_response = client.post("/goals/parse", json=quest_create_payload, headers=auth_headers)
    assert quests_response.status_code == 200, f"Quest creation via /goals/parse failed: {quests_response.text}"
    # Assuming /goals/parse returns a list of quests, and we take the first one.
    # This structure needs to match what /goals/parse actually returns.
    created_quests = quests_response.json()
    assert created_quests and len(created_quests) > 0, "No quests returned from /goals/parse"
    quest_id = created_quests[0]["id"]


    # 3. Process Accomplishment with quest_id
    accomplishment_payload = {
        "name": "Completed Task for Quest",
        "description": "This fulfills the test quest.",
        "quest_id": quest_id, # quest_id is a string here, Pydantic will convert to UUID
    }

    # Use a spy to verify the CRUD function call
    # graph_crud.create_accomplishment is called within a session.execute_write
    # The spy should wrap the actual graph_crud.create_accomplishment
    with patch("api.graph_crud.create_accomplishment", wraps=graph_crud.create_accomplishment) as spy_create_accomplishment:
        # The endpoint was changed from /accomplishments/process to /process
        response = client.post("/accomplishments/process", json=accomplishment_payload, headers=auth_headers)
        assert response.status_code == 200, response.text

        # Assert that the spy was called correctly
        spy_create_accomplishment.assert_called_once()
        call_args = spy_create_accomplishment.call_args

        # args[0] is the transaction (tx)
        # args[1] is user_email
        # args[2] is accomplishment_payload (dict)
        # kwargs should contain quest_id

        assert call_args[0][1] == user_email  # user_email from token
        assert call_args[0][2]["name"] == "Completed Task for Quest"  # name from payload dict
        assert "user_email" not in call_args[0][2] # user_email should not be in this dict
        # quest_id is passed as a keyword argument to the CRUD function
        assert str(call_args[1].get("quest_id")) == str(quest_id) # Compare as strings or UUIDs


def test_process_accomplishment_for_non_existent_user(clean_db_client):
    client = clean_db_client
    non_existent_user_email = "ghost@example.com"

    # Define a mock user object that will be returned by the dependency
    def mock_get_current_user_for_ghost():
        # Ensure the mock User object matches the fields expected by the application.
        # User ID is an int, is_active is a bool.
        # The User model from schemas.py might not have 'name' directly, check its definition.
        # Based on schemas.py User(UserBase) -> email; id, is_active added in User.
        # Let's assume User model is {id: int, email: str, is_active: bool} for the token context
        return User(id=999, email=non_existent_user_email, is_active=True)


    # Override the dependency for this specific test
    # The client object from clean_db_client has its own app instance.
    client.app.dependency_overrides[get_current_user] = mock_get_current_user_for_ghost

    # This payload is now correct as it does not contain `user_email`
    accomplishment_payload = {
        "name": "Accomplishment for Ghost",
        "description": "This should fail with 404.",
    }
    # The endpoint was changed from /accomplishments/process to /process
    # Need to include auth headers, even if user is a ghost, for dependency to resolve
    response = client.post("/accomplishments/process", json=accomplishment_payload, headers={"Authorization": "Bearer faketoken"})


    # Clean up the override to not affect other tests
    # Accessing app directly like this might be an issue if `clean_db_client` scopes app instance locally.
    # It's better if the fixture handles its own cleanup or the override is context-managed.
    # For now, assuming this clear works as intended by the user.
    client.app.dependency_overrides.clear()

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
    assert non_existent_user_email in response.json()["detail"]
