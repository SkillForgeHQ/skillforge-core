import pytest
import uuid
from fastapi.testclient import TestClient
from jose import jwt

# Imports required by the new test function
from unittest import mock # Make sure this is imported
from api.routers.auth import get_current_user # Corrected path
from api.schemas import User
# ... other existing imports ...


def test_issue_vc_for_accomplishment(monkeypatch, test_keys, clean_db_client):
    client = clean_db_client  # Use the fixture that provides a clean database
    """
    Tests the full loop:
    1. Create a user and an accomplishment.
    2. Call the endpoint to issue a VC.
    3. Decode the resulting JWT with the public key and verify its contents.
    """
    # Use monkeypatch to make the app use the temporary test key
    original_open = open

    def mock_open(file, *args, **kwargs):
        # If the application code specifically asks for "private_key.json",
        # redirect it to the temporary key file created by the test_keys fixture.
        if file == "private_key.json":
            return original_open(test_keys["private_key_path"], *args, **kwargs)
        # Fallback for any other file access (though not expected for this specific part of the test)
        return original_open(file, *args, **kwargs)

    monkeypatch.setattr("builtins.open", mock_open)

    # Mock the skill_extractor_chain where it's used in the router
    from unittest.mock import AsyncMock, MagicMock
    from api.ai.schemas import ExtractedSkills, SkillLevel

    mock_chain_instance = MagicMock()
    mock_extracted_skills_response = ExtractedSkills(
        skills=[
            SkillLevel(skill="Python", level="Intermediate"),
            SkillLevel(skill="FastAPI", level="Beginner"),
        ]
    )
    mock_chain_instance.ainvoke = AsyncMock(return_value=mock_extracted_skills_response)

    # accomplishments.router imports skill_extractor_chain from ..ai.skill_extractor
    # So we patch it in api.routers.accomplishments
    monkeypatch.setattr("api.routers.accomplishments.skill_extractor_chain", mock_chain_instance)

    # Mock the find_skill_match function where it's used in the router
    from api.ai.schemas import SkillMatch # Corrected to SkillMatch

    async def mock_find_skill_match(candidate_skill_name, existing_skill_names):
        # For simplicity, assume no skills are duplicates for the test
        return SkillMatch(is_duplicate=False, existing_skill_name=None)

    monkeypatch.setattr("api.routers.accomplishments.find_skill_match", mock_find_skill_match)

    # STEP 1: Create the necessary data (user and accomplishment)
    unique_id = uuid.uuid4().hex[:8]  # Use a portion of a UUID for uniqueness
    user_email = f"test.vc.user.{unique_id}@skillforge.io"
    user_password = "asecurepassword" # Store password for login
    user_payload = {"email": user_email, "name": "VC Test User", "password": user_password}
    response = clean_db_client.post("/users/", json=user_payload)
    assert user_response.status_code == 201, f"User creation failed or returned unexpected status: {user_response.text}"
    # created_user_data = user_response.json() # User data if needed, like ID

    # Log in the new user to get a token
    login_data = {"username": user_email, "password": user_password}
    token_response = clean_db_client.post("/token", data=login_data)
    assert token_response.status_code == 200, f"Failed to get token: {token_response.text}"
    access_token = token_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    accomplishment_payload = {
        # "user_email": user_email, # Field removed from schema
        "name": "Built a Test Case",
        "description": "Successfully wrote a pytest case for VC generation.",
        # proof_url is optional
    }
    # Use the correct endpoint and auth headers
    response = clean_db_client.post(
        "/accomplishments/process", json=accomplishment_payload, headers=auth_headers
    )
    assert response.status_code == 200, f"Accomplishment processing failed: {response.text}"
    # Extract accomplishment ID from the new response structure
    accomplishment_id = response.json()["accomplishment"]["id"]

    # STEP 2: Call the new endpoint to issue the credential
    # This endpoint might also require auth depending on its definition, but test_keys implies it might not if using issuer key directly
    # For now, let's assume it doesn't need user auth if it's an admin-like action or uses a different auth mechanism.
    # If it requires user auth, add headers=auth_headers
    vc_response = client.post(f"/accomplishments/{accomplishment_id}/issue-credential") # Assuming no auth needed for this specific test setup
    assert vc_response.status_code == 200

    signed_vc_jwt = vc_response.json()["verifiable_credential_jwt"]
    assert signed_vc_jwt is not None

    # STEP 3: Decode and verify the JWT
    public_pem = test_keys["public_key"].export_to_pem()
    decoded_token = jwt.decode(
        signed_vc_jwt, public_pem, algorithms=["ES256"], issuer=test_keys["issuer_id"]
    )

    # Assert claims in the JWT
    assert decoded_token["iss"] == test_keys["issuer_id"]

    # Assert claims within the Verifiable Credential payload
    vc_payload = decoded_token["vc"]
    assert vc_payload["type"] == ["VerifiableCredential", "SkillForgeAccomplishment"]
    assert (
        vc_payload["credentialSubject"]["accomplishment"]["name"] == "Built a Test Case"
    )


def test_process_accomplishment_with_quest_id(monkeypatch, clean_db_client, test_keys):
    client = clean_db_client
    original_open = open

    def mock_open(file, *args, **kwargs):
        if file == "private_key.json":
            return original_open(test_keys["private_key_path"], *args, **kwargs)
        return original_open(file, *args, **kwargs)

    monkeypatch.setattr("builtins.open", mock_open)

    from unittest.mock import AsyncMock, MagicMock, patch
    from api.ai.schemas import ExtractedSkills, SkillLevel, SkillMatch

    # Mock AI services
    mock_chain_instance = MagicMock()
    mock_extracted_skills_response = ExtractedSkills(skills=[SkillLevel(skill="Testing", level="Advanced")])
    mock_chain_instance.ainvoke = AsyncMock(return_value=mock_extracted_skills_response)
    monkeypatch.setattr("api.routers.accomplishments.skill_extractor_chain", mock_chain_instance)

    async def mock_find_skill_match(candidate_skill_name, existing_skill_names):
        return SkillMatch(is_duplicate=False, existing_skill_name=None)
    monkeypatch.setattr("api.routers.accomplishments.find_skill_match", mock_find_skill_match)

    # 1. Create User
    unique_id = uuid.uuid4().hex[:8]
    user_email = f"test.quest.user.{unique_id}@skillforge.io"
    user_password = "securepassword"
    user_payload = {"email": user_email, "name": "Quest Test User", "password": user_password}
    user_response = clean_db_client.post("/users/", json=user_payload)
    assert user_response.status_code == 201, user_response.text

    # Log in to get token
    login_data = {"username": user_email, "password": user_password}
    token_response = clean_db_client.post("/token", data=login_data)
    access_token = token_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Create a Quest
    quest_create_payload = {"name": "My Test Quest", "description": "Quest for testing accomplishments."}
    quest_response = clean_db_client.post("/quests/", json=quest_create_payload, headers=auth_headers)
    assert quest_response.status_code == 200, quest_response.text
    created_quest = quest_response.json()
    quest_id = created_quest["id"]

    # 3. Process Accomplishment with quest_id
    # The user_email field is now correctly removed from the payload.
    accomplishment_payload = {
        "name": "Completed Task for Quest",
        "description": "This accomplishment fulfills the test quest.",
        "quest_id": quest_id
    }

    with patch("api.graph_crud.create_accomplishment") as mock_create_accomplishment_crud:
        mock_returned_node_data = {
            "id": uuid.uuid4(),
            "name": accomplishment_payload["name"],
            "description": accomplishment_payload["description"],
            "proof_url": None,
            "timestamp": "2023-01-01T12:00:00Z",
        }
        mock_create_accomplishment_crud.return_value = mock_returned_node_data

        acc_response = client.post("/accomplishments/process", json=accomplishment_payload, headers=auth_headers)
        assert acc_response.status_code == 200, acc_response.text

        response_data = acc_response.json()
        assert response_data["accomplishment"]["name"] == accomplishment_payload["name"]

        # Verify that graph_crud.create_accomplishment was called correctly.
        mock_create_accomplishment_crud.assert_called_once()
        args, kwargs = mock_create_accomplishment_crud.call_args

        # Verify the user is identified from the token, not the payload.
        # args[0] is the transaction (tx), args[1] is the user object.
        assert args[1].email == user_email

        # Verify quest_id is passed as a kwarg.
        assert isinstance(kwargs.get("quest_id"), uuid.UUID)
        assert str(kwargs.get("quest_id")) == quest_id

        # Verify the accomplishment data is passed correctly.
        # args[2] is the accomplishment data dictionary.
        assert args[2]["name"] == accomplishment_payload["name"]
        assert args[2]["description"] == accomplishment_payload["description"]
        assert "user_email" not in args[2]
        assert "quest_id" not in args[2]


def test_process_accomplishment_advances_goal(monkeypatch, clean_db_client, test_keys):
    client = clean_db_client
    # ... [Copy mocks from previous tests] ...
    original_open = open

    def mock_open(file, *args, **kwargs):
        if file == "private_key.json":
            return original_open(test_keys["private_key_path"], *args, **kwargs)
        return original_open(file, *args, **kwargs)

    monkeypatch.setattr("builtins.open", mock_open)

    from unittest.mock import AsyncMock, MagicMock, patch
    from api.ai.schemas import ExtractedSkills, SkillLevel, SkillMatch

    # Mock AI services
    mock_chain_instance = MagicMock()
    mock_extracted_skills_response = ExtractedSkills(skills=[SkillLevel(skill="Testing", level="Advanced")])
    mock_chain_instance.ainvoke = AsyncMock(return_value=mock_extracted_skills_response)
    monkeypatch.setattr("api.routers.accomplishments.skill_extractor_chain", mock_chain_instance)

    async def mock_find_skill_match(candidate_skill_name, existing_skill_names):
        return SkillMatch(is_duplicate=False, existing_skill_name=None)
    monkeypatch.setattr("api.routers.accomplishments.find_skill_match", mock_find_skill_match)


    # 1. Create User
    unique_id = uuid.uuid4().hex[:8]
    user_email = f"test.goal.advancement.{unique_id}@skillforge.io"
    user_password = "securepassword"
    clean_db_client.post("/users/", json={"email": user_email, "name": "Goal Advancement User", "password": user_password})
    token_response = clean_db_client.post("/token", data={"username": user_email, "password": user_password})
    assert token_response.status_code == 200, f"Failed to get token: {token_response.text}"
    auth_headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}

    # 2. Create Goal with a plan
    goal_plan = {
        "title": "Learn FastAPI",
        "steps": [
            {"title": "Step 1: Read the docs", "description": "Read the official FastAPI documentation."},
            {"title": "Step 2: Build a simple API", "description": "Create a hello world API."},
        ]
    }
    goal_payload = {"goal_text": "Learn FastAPI", "full_plan_json": str(goal_plan)}
    # This part needs an endpoint to create a goal and get back the first quest
    # For now, let's assume the first quest is created and we have its ID
    # In a real scenario, the /goals/parse endpoint would be called
    # Let's manually create the first quest for the test
    quest_create_payload = {"name": "Step 1: Read the docs", "description": "Read the official FastAPI documentation."}
    quest_response = clean_db_client.post("/quests/", json=quest_create_payload, headers=auth_headers)
    first_quest_id = quest_response.json()["id"]

    # 3. Process accomplishment for the first quest
    accomplishment_payload = {
        "name": "Finished reading the docs",
        "description": "I have read all the FastAPI docs.",
        "quest_id": first_quest_id
    }

    # 4. Patch `advance_goal` to verify it's called
    with patch("api.graph_crud.advance_goal") as mock_advance_goal:
        response = client.post("/accomplishments/process", json=accomplishment_payload, headers=auth_headers)
        assert response.status_code == 200

        # Verify that advance_goal was called with the correct quest_id and user_email
        mock_advance_goal.assert_called_once()
        call_args = mock_advance_goal.call_args[0]
        assert call_args[1] == first_quest_id
        assert call_args[2] == user_email


def test_process_accomplishment_for_non_existent_user(clean_db_client):
    """
    Tests that a 404 is returned when processing an accomplishment
    for a user that does not exist in the database.
    """
    client = clean_db_client
    non_existent_user_email = "ghost@example.com"

    # Mock the authenticated user for this request
    def mock_get_current_user_for_ghost():
        return User(id=9999, email=non_existent_user_email, is_active=True)

    client.app.dependency_overrides[get_current_user] = mock_get_current_user_for_ghost

    from unittest.mock import AsyncMock, MagicMock, patch
    from api.ai.schemas import ExtractedSkills, SkillMatch

    # 1. Patch the entire `skill_extractor_chain` object, not a method on it.
    with patch("api.routers.accomplishments.skill_extractor_chain", new_callable=MagicMock) as mock_skill_extractor_chain, \
         patch("api.routers.accomplishments.find_skill_match", new_callable=AsyncMock, return_value=SkillMatch(is_duplicate=False, existing_skill_name=None)), \
         patch("api.graph_crud.user_exists") as mock_user_exists_crud:

        # 2. Configure the `.ainvoke()` method on the new mock object.
        mock_skill_extractor_chain.ainvoke = AsyncMock(return_value=ExtractedSkills(skills=[]))

        # 3. Mock the database check to return False, simulating a non-existent user.
        mock_user_exists_crud.return_value = False

        accomplishment_payload = {
            "name": "Task for Ghost",
            "description": "This should fail because the user does not exist."
        }

        # 4. Make the request and assert the expected outcome.
        response = clean_db_client.post(
            "/accomplishments/process",
            json=accomplishment_payload,
            headers={"Authorization": "Bearer fake-token-for-ghost"} # Token is for auth, user identity from mock_get_current_user
        )

        assert response.status_code == 404, response.text
        assert response.json()["detail"] == f"User with email {non_existent_user_email} not found."
        mock_user_exists_crud.assert_called_once_with(mock.ANY, non_existent_user_email)

    # Clean up the dependency override to not affect other tests
    client.app.dependency_overrides = {}
