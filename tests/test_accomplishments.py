# tests/test_accomplishments.py

import pytest
import uuid
from jose import jwt
from unittest.mock import patch, AsyncMock, MagicMock

from api.routers.auth import get_current_user
from api.schemas import User # User is correctly in api.schemas
from api.ai.schemas import ExtractedSkills, SkillLevel, SkillMatch # AI schemas are in api.ai.schemas
from api import graph_crud

# NOTE: The TestClient is now provided by the `clean_db_client` fixture.

def test_issue_vc_for_accomplishment(monkeypatch, test_keys, clean_db_client):
    client = clean_db_client

    original_open = open
    def mock_open(file, *args, **kwargs):
        if file == "private_key.json":
            return original_open(test_keys["private_key_path"], *args, **kwargs)
        return original_open(file, *args, **kwargs)
    monkeypatch.setattr("builtins.open", mock_open)

    mock_chain = MagicMock()
    mock_chain.ainvoke = AsyncMock(return_value=ExtractedSkills(skills=[]))
    monkeypatch.setattr("api.routers.accomplishments.skill_extractor_chain", mock_chain)

    # Mock find_skill_match as well for the VC test path if it involves skill processing
    async def mock_find_skill_match_vc(candidate_skill_name, existing_skill_names):
        return SkillMatch(is_duplicate=False, existing_skill_name=None)
    monkeypatch.setattr("api.routers.accomplishments.find_skill_match", mock_find_skill_match_vc)

    user_email = f"test.vc.user.{uuid.uuid4().hex[:6]}@skillforge.io"
    client.post("/users/", json={"email": user_email, "name": "VC Test", "password": "password"})
    token_resp = client.post("/token", data={"username": user_email, "password": "password"})
    headers = {"Authorization": f"Bearer {token_resp.json()['access_token']}"}

    acc_resp = client.post("/accomplishments/process", json={"name": "Test VC", "description": "Desc"}, headers=headers)
    assert acc_resp.status_code == 200, acc_resp.text # Ensure accomplishment processing is successful
    accomplishment_id = acc_resp.json()["accomplishment"]["id"]

    vc_resp = client.post(f"/accomplishments/{accomplishment_id}/issue-credential", headers=headers) # Assuming issue-credential might also need auth
    assert vc_resp.status_code == 200, vc_resp.text

    decoded = jwt.decode(vc_resp.json()["verifiable_credential_jwt"], test_keys["public_key"].export_to_pem(), algorithms=["ES256"], issuer=test_keys["issuer_id"])
    assert decoded["vc"]["credentialSubject"]["accomplishment"]["name"] == "Test VC"

def test_process_accomplishment_with_quest_id(monkeypatch, clean_db_client):
    client = clean_db_client

    # Mock AI services
    mock_chain = MagicMock()
    mock_chain.ainvoke = AsyncMock(return_value=ExtractedSkills(skills=[SkillLevel(skill="Testing", level="Advanced")]))
    monkeypatch.setattr("api.routers.accomplishments.skill_extractor_chain", mock_chain)

    async def mock_find_skill(c, e): return SkillMatch(is_duplicate=False, existing_skill_name="Testing")
    monkeypatch.setattr("api.routers.accomplishments.find_skill_match", mock_find_skill)

    # 1. Create User and Log In
    user_email = f"test.quest.user.{uuid.uuid4().hex[:6]}@skillforge.io"
    client.post("/users/", json={"email": user_email, "name": "Quest User", "password": "password"})
    token_resp = client.post("/token", data={"username": user_email, "password": "password"})
    headers = {"Authorization": f"Bearer {token_resp.json()['access_token']}"}

    # 2. Create Quest
    # Mock the response from the goals parser for simplicity and isolation
    quest_id = str(uuid.uuid4())
    # The user's provided test code for goals.parse returns a list of dicts.
    # Ensuring the mock matches this structure.
    mock_parsed_quests = [{"id": quest_id, "name": "Test Quest", "description": "A quest from the parser."}]

    # Patching the function within the router where it's called
    # Assuming 'parse_goal_into_subtasks' is in 'api.routers.goals'
    # Note: The user's test code implies `create_quest_and_link_to_user` is called by `/goals/parse`
    # We'll mock what the user's test code was trying to achieve with the spy on create_quest_and_link_to_user
    # For simplicity of this test, we will directly mock the output of /goals/parse if it's just for getting a quest_id
    # The user's test had `with patch("api.routers.goals.create_quest_and_link_to_user", wraps=graph_crud.create_quest_and_link_to_user) as spy_create_quest:`
    # This suggests /goals/parse calls that CRUD function.
    # Let's simplify the mocking for this test to focus on the accomplishment part.
    # We just need a quest_id.
    with patch("api.routers.goals.parse_goal_into_subtasks", return_value=mock_parsed_quests) as mock_parse_goal:
        quests_resp = client.post("/goals/parse", json={"goal": "Test a quest"}, headers=headers)
        assert quests_resp.status_code == 200, quests_resp.text
        retrieved_quest_id = quests_resp.json()[0]["id"]
        assert retrieved_quest_id == quest_id


    # 3. Process Accomplishment with quest_id
    accomplishment_payload = {"name": "Completed Quest Task", "description": "Desc.", "quest_id": quest_id}

    with patch("api.graph_crud.create_accomplishment", wraps=graph_crud.create_accomplishment) as spy_create_acc:
        response = client.post("/accomplishments/process", json=accomplishment_payload, headers=headers)
        assert response.status_code == 200, response.text

        spy_create_acc.assert_called_once()
        call_args = spy_create_acc.call_args
        # call_args.args is the tuple of positional arguments
        assert call_args.args[1] == user_email # user_email from token
        assert call_args.args[2]["name"] == "Completed Quest Task" # name from payload dict
        assert "user_email" not in call_args.args[2] # user_email should not be in this dict
        # call_args.kwargs is the dict of keyword arguments
        assert str(call_args.kwargs.get("quest_id")) == quest_id


def test_process_accomplishment_for_non_existent_user(clean_db_client):
    client = clean_db_client

    def mock_get_current_user():
        # Ensure this User model matches what api.schemas.User provides for token data
        return User(id=999, email="ghost@example.com", is_active=True)

    client.app.dependency_overrides[get_current_user] = mock_get_current_user

    response = client.post("/accomplishments/process", json={"name": "Ghost Acc", "description": "Desc."}, headers={"Authorization": "Bearer faketoken"})

    client.app.dependency_overrides.clear()

    assert response.status_code == 404, response.text
    assert "not found" in response.json()["detail"].lower()
