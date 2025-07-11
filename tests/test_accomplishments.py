import pytest
import uuid
from fastapi.testclient import TestClient
from jose import jwt
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
    user_payload = {"email": user_email, "name": "VC Test User", "password": user_password}
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
        # "user_email": user_email, # Field removed from schema
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
    user_response = client.post("/users/", json=user_payload)
    assert user_response.status_code == 201, user_response.text

    # Log in to get token
    login_data = {"username": user_email, "password": user_password}
    token_response = client.post("/token", data=login_data)
    access_token = token_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Create a Quest
    # No need to mock graph_db_session for quests if it uses the main DB normally
    # and the clean_db_client fixture ensures the DB is ready.
    # If quest creation is simple and doesn't involve complex graph operations that need mocking for this test,
    # we can let it hit the test graph DB.
    quest_create_payload = {"name": "My Test Quest", "description": "Quest for testing accomplishments."}
    # Assuming quest creation doesn't require special auth for this test flow, or uses the same user token
    quest_response = client.post("/quests/", json=quest_create_payload, headers=auth_headers) # Added auth if needed
    assert quest_response.status_code == 200, quest_response.text # FastAPI default is 200 for POST if not specified
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
        # Mock return value for graph_crud.create_accomplishment
        # This node should represent what's stored and then used to build the response.
        # It should align with the Accomplishment schema for response validation.
        # Note: user_email and quest_id are not part of the node properties in the graph typically,
        # but are used for creating relationships or are part of the response model.
        # The mock here should return what the `AccomplishmentSchema.model_validate` would expect.
        mock_returned_node_data = {
            "id": uuid.uuid4(), # Simulate DB-generated ID
            "name": accomplishment_payload["name"],
            "description": accomplishment_payload["description"],
            "proof_url": None, # Assuming no proof_url sent
            "timestamp": "2023-01-01T12:00:00Z", # Simulate DB-generated timestamp
            # user_email is not stored on the node but added to response from current_user
            # quest_id is not stored on the node but used for relationship
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
        # The quest_id in the payload is a string, Pydantic converts it to UUID for the AccomplishmentCreate model.
        # This UUID is then passed to the CRUD function.
        assert isinstance(kwargs.get("quest_id"), uuid.UUID)
        assert str(kwargs.get("quest_id")) == quest_id


        # Verify the accomplishment data is passed correctly.
        # args[2] is the accomplishment data dictionary. This comes from accomplishment_data.model_dump(exclude_unset=True)
        # after quest_id has been popped. It should not contain user_email as that was removed from AccomplishmentCreate.
        assert args[2]["name"] == accomplishment_payload["name"]
        assert args[2]["description"] == accomplishment_payload["description"]
        assert "user_email" not in args[2] # Explicitly check user_email is NOT in the payload dict
        assert "quest_id" not in args[2] # Explicitly check quest_id is NOT in the payload dict (passed separately)


# Make sure to import your app and the dependency you want to override
from api.main import app
# Assuming api.routers.auth is the location of get_current_user based on typical project structure
# If this path is incorrect, the test will fail, and we can adjust it.
from api.routers.auth import get_current_user
from api.schemas import User # User schema for the mock

def test_process_accomplishment_for_non_existent_user(clean_db_client): # Removed monkeypatch
    """
    Tests that a 404 is returned when processing an accomplishment
    for a user that does not exist in the database.
    """
    client = clean_db_client # client from fixture (provides TestClient with its own app instance)
    non_existent_user_email = "ghost@example.com"

    # Define the mock function that will replace the real dependency
    def mock_get_current_user_for_ghost():
        # Ensure the mock User object matches the fields expected by the application.
        # User ID is an int, is_active is a bool.
        return User(id=9999, email=non_existent_user_email, is_active=True) # Removed name as it's not in User schema

    # Apply the override to the app instance used by the TestClient from the fixture
    client.app.dependency_overrides[get_current_user] = mock_get_current_user_for_ghost

    # Mock AI services as they might be called if auth passes
    # This part can remain if these services are indeed called before the user_exists check.
    # If user_exists is the very first check after auth, these might not be strictly necessary
    # for this specific test's failure condition, but keeping them doesn't hurt.
    from unittest.mock import AsyncMock, MagicMock, patch # Added patch
    from api.ai.schemas import ExtractedSkills, SkillLevel, SkillMatch

    # For this test, we primarily care that the user_exists check fails.
    # We can simplify AI mocks if they are not crucial for reaching that check.
    # Let's assume they are needed and keep them minimal.
    with patch("api.routers.accomplishments.skill_extractor_chain.ainvoke", new_callable=AsyncMock, return_value=ExtractedSkills(skills=[])) as mock_skill_extract, \
         patch("api.routers.accomplishments.find_skill_match", new_callable=AsyncMock, return_value=SkillMatch(is_duplicate=False)) as mock_skill_match, \
         patch("api.graph_crud.user_exists") as mock_user_exists_crud: # Patch user_exists directly

        # Configure the mock_user_exists_crud to return False for the ghost user
        def side_effect_user_exists(tx, email_to_check): # tx is the first arg for graph_crud.user_exists
            if email_to_check == non_existent_user_email:
                return False
            return True # Default to True for other users if any were created
        mock_user_exists_crud.side_effect = side_effect_user_exists

        accomplishment_payload = {
            # "user_email": non_existent_user_email, # Removed as it's not part of the schema anymore
            "name": "Accomplishment for Ghost",
            "description": "This should fail with a 404.",
        }

        response = client.post("/accomplishments/process", json=accomplishment_payload) # Auth headers are implicitly handled by mock_get_current_user

        # Clean up the override so it doesn't affect other tests
        # app.dependency_overrides.clear() # This is tricky with TestClient from fixture, usually handled by fixture scope
        # The clean_db_client fixture should provide a fresh app or handle overrides correctly.
        # For now, let's assume the fixture handles override cleanup or test isolation.
        # If using pytest's monkeypatch fixture, it handles cleanup automatically.
        # Direct app.dependency_overrides might persist if not cleaned.
        # A better way is to use `with client.app.dependency_overrides(get_current_user=mock_get_current_user_for_ghost):`

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
    assert non_existent_user_email in response.json()["detail"]

    # Explicitly clear overrides if the fixture doesn't handle it, to be safe for subsequent tests.
    # This is important if `app` is a shared instance across tests.
    # However, `clean_db_client` typically creates a new TestClient with a fresh app for each test.
    client.app.dependency_overrides.clear()
