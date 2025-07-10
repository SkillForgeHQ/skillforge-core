import pytest
import uuid
from fastapi.testclient import TestClient
from jose import jwt
from api import schemas as api_schemas # Ensure this import is present
# Removed: from api.main import app

# client = TestClient(app) # Use a fresh client for this test to avoid state issues


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
    # The UserCreate schema does not have a 'name' field.
    user_payload = {"email": user_email, "password": user_password}
    user_response = client.post("/users/", json=user_payload)
    assert user_response.status_code == 201, f"User creation failed or returned unexpected status: {user_response.text}"
    # created_user_data = user_response.json() # User data if needed, like ID

    # Log in the new user to get a token
    login_data = {"username": user_email, "password": user_password}
    token_response = client.post("/token", data=login_data)
    assert token_response.status_code == 200, f"Failed to get token: {token_response.text}"
    access_token = token_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    accomplishment_payload = {
        "user_email": user_email,
        "name": "Built a Test Case",
        "description": "Successfully wrote a pytest case for VC generation.",
        # proof_url is optional
    }
    # Use the correct endpoint and auth headers
    response = client.post(
        "/accomplishments/process", json=accomplishment_payload, headers=auth_headers
    )
    assert response.status_code == 200, f"Accomplishment processing failed: {response.text}"
    # Extract accomplishment ID from the new response structure
    accomplishment_id = response.json()["accomplishment"]["id"]

    # STEP 2: Call the new endpoint to issue the credential
    vc_response = client.post(f"/accomplishments/{accomplishment_id}/issue-credential")
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
    # UserCreate schema does not have 'name'
    user_payload = {"email": user_email, "password": user_password}
    user_response = client.post("/users/", json=user_payload)
    assert user_response.status_code == 201, user_response.text

    # Log in to get token
    login_data = {"username": user_email, "password": user_password}
    token_response = client.post("/token", data=login_data)
    access_token = token_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Create a Quest (using the new endpoint)
    mock_quest_db_session = MagicMock()

    def mock_quest_write_transaction(func, quest_data_dict):
        # Simulate quest creation in DB for the /quests/ endpoint call
        return { "id": uuid.uuid4(), **quest_data_dict }

    mock_quest_db_session.write_transaction = mock_quest_write_transaction

    with patch("api.routers.quests.get_graph_db_session") as mock_get_quest_db:
        mock_get_quest_db.return_value.__enter__.return_value = mock_quest_db_session

        quest_create_payload = {"name": "My Test Quest", "description": "Quest for testing accomplishments."}
        quest_response = client.post("/quests/", json=quest_create_payload)
        assert quest_response.status_code == 200, quest_response.text
        created_quest = quest_response.json()
        quest_id = created_quest["id"]

    # 3. Process Accomplishment with quest_id
    accomplishment_payload = {
        "user_email": user_email,
        "name": "Completed Task for Quest",
        "description": "This accomplishment fulfills the test quest.",
        "quest_id": quest_id
    }

    with patch("api.graph_crud.create_accomplishment") as mock_create_accomplishment_crud:
        mock_accomplishment_node = {
            "id": uuid.uuid4(),
            "name": accomplishment_payload["name"],
            "description": accomplishment_payload["description"],
            "proof_url": None,
            "timestamp": "2023-01-01T12:00:00Z",
            "user_email": user_email,
            "quest_id": quest_id
        }
        mock_create_accomplishment_crud.return_value = mock_accomplishment_node

        acc_response = client.post("/accomplishments/process", json=accomplishment_payload, headers=auth_headers)
        assert acc_response.status_code == 200, acc_response.text

        response_data = acc_response.json()
        assert response_data["accomplishment"]["name"] == accomplishment_payload["name"]

        mock_create_accomplishment_crud.assert_called_once()
        args, kwargs = mock_create_accomplishment_crud.call_args
        assert str(kwargs.get("quest_id")) == quest_id
        assert args[1] == user_email

        # Corrected assertion for args[2]
        # It should contain user_email because AccomplishmentCreate includes it
        expected_crud_payload_dict = {
            "user_email": user_email,
            "name": accomplishment_payload["name"],
            "description": accomplishment_payload["description"],
            # proof_url is optional and not in payload, so it won't be in model_dump(exclude_unset=True)
        }
        assert args[2] == expected_crud_payload_dict


def test_process_accomplishment_non_existent_user(clean_db_client, monkeypatch):
    client = clean_db_client

    from unittest.mock import AsyncMock, MagicMock
    from api.ai.schemas import ExtractedSkills, SkillLevel, SkillMatch
    from api import crud # Import crud to get its original function

    mock_chain_instance = MagicMock()
    mock_extracted_skills_response = ExtractedSkills(skills=[])
    mock_chain_instance.ainvoke = AsyncMock(return_value=mock_extracted_skills_response)
    monkeypatch.setattr("api.routers.accomplishments.skill_extractor_chain", mock_chain_instance)

    async def mock_find_skill_match(candidate_skill_name, existing_skill_names):
        return SkillMatch(is_duplicate=False, existing_skill_name=None)
    monkeypatch.setattr("api.routers.accomplishments.find_skill_match", mock_find_skill_match)

    unique_id = uuid.uuid4().hex[:8]
    user_email_for_test = f"user.stateful.mock.{unique_id}@skillforge.io"
    user_password = "password123"

    # UserCreate schema does not require 'name' but our test payload for /users/ includes it.
    # The /users/ endpoint should ideally ignore extra fields or UserCreate should include 'name' if it's stored.
    # For now, we assume /users/ POST correctly creates the user and returns data for login.
    user_payload_for_creation = {"email": user_email_for_test, "name": "Stateful Mock Test User", "password": user_password}
    user_creation_response = client.post("/users/", json=user_payload_for_creation)
    assert user_creation_response.status_code == 201, f"User creation failed: {user_creation_response.text}"

    created_user_response_json = user_creation_response.json()
    # Data for creating api_schemas.User instance. It must match fields in api_schemas.User
    # api_schemas.User has: id, email, is_active.
    # The /users/ POST response (schemas.User) returns id, email, is_active.
    created_user_data_for_mock = {
        "id": created_user_response_json["id"],
        "email": created_user_response_json["email"],
        # "name" is not part of schemas.User, so not needed here for the Pydantic model
        "is_active": created_user_response_json.get("is_active", True)
    }

    login_data = {"username": user_email_for_test, "password": user_password}
    token_response = client.post("/token", data=login_data)
    assert token_response.status_code == 200, f"Token retrieval failed: {token_response.text}"
    access_token = token_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    original_api_crud_get_user_by_email = crud.get_user_by_email

    class CallCounter:
        def __init__(self):
            self.count = 0
        def increment(self):
            self.count += 1
        def current_count(self):
            return self.count

    counter = CallCounter()

    def mock_get_user_by_email_stateful(db_conn, *, email):
        counter.increment()
        if email == user_email_for_test:
            if counter.current_count() == 1:
                # Return a Pydantic User model instance for the auth layer
                # This dict must match the fields of api_schemas.User for successful validation
                return api_schemas.User(**created_user_data_for_mock)
            elif counter.current_count() == 2:
                return None
        return original_api_crud_get_user_by_email(db_conn, email=email)

    monkeypatch.setattr("api.crud.get_user_by_email", mock_get_user_by_email_stateful)

    accomplishment_payload_for_endpoint = {
        "user_email": user_email_for_test,
        "name": "Test Accomplishment for Stateful Mock",
        "description": "This should now trigger the 404 from process_accomplishment.",
    }

    response = client.post(
        "/accomplishments/process", json=accomplishment_payload_for_endpoint, headers=auth_headers
    )

    assert response.status_code == 404, f"Expected 404, got {response.status_code}. Response: {response.text}"
    assert response.json()["detail"] == "User not found"

    monkeypatch.setattr("api.crud.get_user_by_email", original_api_crud_get_user_by_email)
