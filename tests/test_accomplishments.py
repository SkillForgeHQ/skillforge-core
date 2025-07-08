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
