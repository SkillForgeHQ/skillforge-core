import pytest
import uuid
from fastapi.testclient import TestClient
from jose import jwt
from api.main import app  # Adjust import as needed

# client = TestClient(app) # Use a fresh client for this test to avoid state issues


def test_issue_vc_for_accomplishment(monkeypatch, test_keys):
    client = TestClient(app)  # Create a new client for this test
    """
    Tests the full loop:
    1. Create a user and an accomplishment.
    2. Call the endpoint to issue a VC.
    3. Decode the resulting JWT with the public key and verify its contents.
    """
    # Use monkeypatch to make the app use the temporary test key
    original_open = open

    def mock_open(file, *args, **kwargs):
        if file == test_keys["private_key_path"]:
            return original_open(test_keys["private_key_path"], *args, **kwargs)
        return original_open(file, *args, **kwargs)

    monkeypatch.setattr("builtins.open", mock_open)

    # STEP 1: Create the necessary data (user and accomplishment)
    unique_id = uuid.uuid4().hex[:8]  # Use a portion of a UUID for uniqueness
    user_email = f"test.vc.user.{unique_id}@skillforge.io"
    user_payload = {"email": user_email, "name": "VC Test User", "password": "asecurepassword"}
    user_response = client.post("/users/", json=user_payload)
    assert user_response.status_code == 200, f"Failed to create user: {user_response.text}"

    accomplishment_payload = {
        "name": "Built a Test Case",
        "description": "Successfully wrote a pytest case for VC generation.",
    }
    response = client.post(
        f"/users/{user_email}/accomplishments", json=accomplishment_payload
    )
    assert response.status_code == 200
    accomplishment_id = response.json()["id"]

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
