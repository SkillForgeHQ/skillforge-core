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
        "user_email": user_email, # Added user_email
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

    # 2. Create a Quest (using the new endpoint)
    # We need to mock the graph_db_session for the quests router as well
    mock_quest_db_session = MagicMock()

    def mock_quest_write_transaction(func, quest_data_dict):
        # Simulate quest creation in DB for the /quests/ endpoint call
        return { "id": uuid.uuid4(), **quest_data_dict }

    mock_quest_db_session.write_transaction = mock_quest_write_transaction

    # Patch where get_graph_db_session is imported in api.routers.quests
    with patch("api.routers.quests.get_graph_db_session") as mock_get_quest_db:
        mock_get_quest_db.return_value.__enter__.return_value = mock_quest_db_session

        quest_create_payload = {"name": "My Test Quest", "description": "Quest for testing accomplishments."}
        quest_response = client.post("/quests/", json=quest_create_payload) # No auth for quest creation in this example
        assert quest_response.status_code == 200, quest_response.text
        created_quest = quest_response.json()
        quest_id = created_quest["id"]

    # 3. Process Accomplishment with quest_id
    accomplishment_payload = {
        "user_email": user_email, # Added user_email
        "name": "Completed Task for Quest",
        "description": "This accomplishment fulfills the test quest.",
        "quest_id": quest_id
    }

    # Mock the graph_crud.create_accomplishment to verify it's called with quest_id
    # This mock will apply to the call within the /accomplishments/process endpoint
    with patch("api.graph_crud.create_accomplishment") as mock_create_accomplishment_crud:
        # Define what the mocked CRUD function should return
        # It needs to return a dictionary that can be validated by AccomplishmentSchema
        mock_accomplishment_node = {
            "id": uuid.uuid4(),
            "name": accomplishment_payload["name"],
            "description": accomplishment_payload["description"],
            "proof_url": None,
            "timestamp": "2023-01-01T12:00:00Z", # Example timestamp
            "user_email": user_email, # Added user_email for schema validation
            "quest_id": quest_id # Added quest_id for schema validation
        }
        mock_create_accomplishment_crud.return_value = mock_accomplishment_node

        acc_response = client.post("/accomplishments/process", json=accomplishment_payload, headers=auth_headers)
        assert acc_response.status_code == 200, acc_response.text

        response_data = acc_response.json()
        assert response_data["accomplishment"]["name"] == accomplishment_payload["name"]
        # The quest_id is part of the AccomplishmentCreate schema but not directly in Accomplishment schema by default.
        # The key is to verify that graph_crud.create_accomplishment was called correctly.

        # Verify that the mock_create_accomplishment_crud was called with the quest_id
        mock_create_accomplishment_crud.assert_called_once()
        args, kwargs = mock_create_accomplishment_crud.call_args
        # args are (tx, user_email, accomplishment_data_dict)
        # kwargs are {quest_id: ...}
        # The quest_id from the payload (string) is converted to UUID by Pydantic model AccomplishmentCreate
        # So, when it's passed to the CRUD function, it's a UUID object.
        # We compare it with the original string quest_id from the test.
        assert str(kwargs.get("quest_id")) == quest_id
        # Ensure user_email is also passed
        assert args[1] == user_email
        # Ensure the main payload (without quest_id) is passed as accomplishment_data
        expected_acc_payload = accomplishment_payload.copy()
        expected_acc_payload.pop("quest_id") # quest_id is passed as a separate kwarg
        # The router also adds user_email to the payload sent to CRUD.
        # However, our schema for AccomplishmentCreate now includes user_email.
        # The router extracts quest_id, and the rest of accomplishment_data (which includes user_email) is passed.
        # So, we need to ensure that the payload sent to CRUD matches what the router prepares.
        # accomplishment_data.model_dump(exclude_unset=True) is used in the router.
        # Let's adjust the assertion for accomplishment_data_dict
        # In the router:
        # accomplishment_payload = accomplishment_data.model_dump(exclude_unset=True)
        # quest_id = accomplishment_payload.pop("quest_id", None)
        # So, args[2] (accomplishment_data_dict) should be accomplishment_payload *without* quest_id but *with* user_email (if it was in the input)
        # The AccomplishmentCreate schema has user_email, so it should be in the model_dump.
        # The current test sends `accomplishment_payload` which does not have user_email.
        # Let's align the test payload with the schema.

        # Re-check payload for `graph_crud.create_accomplishment`
        # The router's `accomplishment_data: AccomplishmentCreate` will have `user_email` from the schema.
        # The test payload `accomplishment_payload` should also include `user_email`.
        # The `current_user.email` is used for the `user_email` argument to `graph_crud.create_accomplishment`.
        # The `accomplishment_data.model_dump()` is used for the `accomplishment_data` argument.

        # Correct assertion for args[2] (the dict passed as accomplishment_data to crud)
        # The router does: `accomplishment_data.model_dump(exclude_unset=True)` then `pop("quest_id")`
        # The input `accomplishment_payload` for the endpoint should match `AccomplishmentCreate`
        # Our `AccomplishmentCreate` schema has `user_email`.
        # The test payload for the endpoint should be:
        # { "name": ..., "description": ..., "quest_id": ..., "user_email": ...}

        # Let's re-evaluate the call to the endpoint and the mock assertion.
        # The `accomplishment_payload` used for `client.post` should include `user_email`.
        # The router will then get `current_user.email` for the first arg to crud,
        # and `accomplishment_data.model_dump().pop('quest_id')` for the second arg.

        # The current `accomplishment_payload` for the endpoint is missing `user_email`.
        # Let's assume the schema `AccomplishmentCreate` has `user_email` and it's populated correctly.
        # The router code is:
        # `accomplishment_payload_dict = accomplishment_data.model_dump(exclude_unset=True)`
        # `quest_id_from_payload = accomplishment_payload_dict.pop("quest_id", None)`
        # `session.write_transaction(graph_crud.create_accomplishment, current_user.email, accomplishment_payload_dict, quest_id=quest_id_from_payload)`
        # So, `args[2]` should be `accomplishment_payload_dict` (which is `accomplishment_data.model_dump()` minus `quest_id`).

        # Our test `accomplishment_payload` sent to the endpoint has `name`, `description`, `quest_id`.
        # The `AccomplishmentCreate` schema also has `user_email`.
        # So, when `accomplishment_data.model_dump(exclude_unset=True)` is called in the router,
        # it will produce a dict with `name`, `description`, `quest_id`, and `user_email`.
        # Then `quest_id` is popped.
        # So `args[2]` should contain `name`, `description`, `user_email`.

        expected_crud_payload = {
            "name": accomplishment_payload["name"],
            "description": accomplishment_payload["description"],
            "user_email": user_email # This comes from the AccomplishmentCreate model
        }
        # The actual payload sent to the endpoint did not include user_email, but the schema implies it.
        # FastAPI would inject it if it's part of the Pydantic model.
        # Let's assume the model binding works and `user_email` is in `accomplishment_data` in the router.

        assert args[2]["name"] == accomplishment_payload["name"]
        assert args[2]["description"] == accomplishment_payload["description"]
        assert args[2]["user_email"] == user_email # This field is in AccomplishmentCreate schema

        # Verify the response structure if needed
        assert response_data["accomplishment"]["name"] == accomplishment_payload["name"]
        # If your AccomplishmentSchema includes quest_id, you can assert it here
        # assert response_data["accomplishment"]["quest_id"] == quest_id
        # However, the provided Accomplishment schema does not have quest_id, so we check the CRUD call.

    # Further check: if you have a way to fetch the accomplishment and see if it's linked to the quest.
    # This would require another DB call, e.g., get_accomplishment_details and check for a FULFILLS relationship.
    # For now, verifying the CRUD call is sufficient for this unit test's scope.


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
        # Ensure the mock User object matches the fields expected by the application
        # (e.g., email, name, potentially others like 'id' or 'disabled' if used by User model).
        # The example from the prompt uses User(email=..., name=...).
        return User(email=non_existent_user_email, name="Ghost User")

    # Apply the override to the app instance used by the TestClient from the fixture
    client.app.dependency_overrides[get_current_user] = mock_get_current_user_for_ghost

    # Mock AI services as they might be called if auth passes
    # This part can remain if these services are indeed called before the user_exists check.
    # If user_exists is the very first check after auth, these might not be strictly necessary
    # for this specific test's failure condition, but keeping them doesn't hurt.
    from unittest.mock import AsyncMock, MagicMock
    from api.ai.schemas import ExtractedSkills, SkillLevel, SkillMatch

    # It's cleaner to use a context manager for monkeypatching if still needed for other parts,
    # or pass monkeypatch as an argument if other mocks within this test require it.
    # For now, assuming AI mocks are set up as they were, if they are still relevant.
    # If `get_current_user` is the only thing to mock for this test path, these can be removed.
    # Let's assume they are still needed for the endpoint to proceed to the user_exists check.

    # Re-creating a simple mock setup for AI parts if they are indeed called.
    # If monkeypatch fixture is removed, these need to be done via app.dependency_overrides too if they are dependencies,
    # or by directly patching the imported objects if they are not FastAPI dependencies.
    # For simplicity, and since the original test had them, let's assume direct patching is okay for these.
    # However, the original test used monkeypatch fixture. If that's removed, this needs rethinking.
    # Let's assume `clean_db_client` doesn't preclude `monkeypatch` if needed for other things.
    # The prompt implies `client` is sufficient, so removing monkeypatch argument.
    # If AI mocks are still needed, they should be done without monkeypatch argument here.

    # The example shows client fixture without monkeypatch, so we will proceed without it for AI mocks too.
    # This implies AI services might not be dependencies injected by FastAPI in the same way, or the test setup handles them.
    # For now, focusing on the get_current_user override.

    accomplishment_payload = {
        "user_email": non_existent_user_email,
        "name": "Accomplishment for Ghost",
        "description": "This should fail with a 404.",
    }

    response = client.post("/accomplishments/process", json=accomplishment_payload)

    # Clean up the override so it doesn't affect other tests
    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
    assert non_existent_user_email in response.json()["detail"]
