import pytest
from fastapi.testclient import TestClient
from jose import jwt
from api.main import app  # Adjust import as needed

client = TestClient(app)


def test_issue_vc_for_accomplishment(monkeypatch, test_keys):
    """
    Tests the full loop:
    1. Create a user and an accomplishment.
    2. Call the endpoint to issue a VC.
    3. Decode the resulting JWT with the public key and verify its contents.
    """
    # Use monkeypatch to make the app use the temporary test key
    monkeypatch.setattr(
        "builtins.open", lambda *args, **kwargs: open(test_keys["private_key_path"])
    )

    # STEP 1: Create the necessary data (user and accomplishment)
    user_email = "test.vc.user@skillforge.io"
    client.post("/users/", json={"email": user_email, "name": "VC Test User"})

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
