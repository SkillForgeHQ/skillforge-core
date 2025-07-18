from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel
from typing import List
from neo4j import Driver

from ..ai.schemas import SkillLevel
from ..ai.skill_extractor import skill_extractor_chain
from ..ai.skill_matcher import find_skill_match

# Database Imports
from ..database import get_graph_db_driver
from .. import graph_crud
from ..schemas import AccomplishmentCreate, Accomplishment as AccomplishmentSchema, User

# Security Imports
from .auth import get_current_user
from fastapi import APIRouter, Depends, HTTPException

from jose import jwt
from jwcrypto import jwk
import json
import datetime
import uuid
import os # Added for os.getenv

router = APIRouter()


class AccomplishmentResponse(BaseModel):
    message: str
    accomplishment: AccomplishmentSchema


@router.post(
    "/accomplishments/process",
    response_model=AccomplishmentResponse,
    tags=["Accomplishments"],
)
async def process_accomplishment(
    accomplishment_data: AccomplishmentCreate = Body(...),
    driver: Driver = Depends(get_graph_db_driver),
    current_user: User = Depends(get_current_user),
):
    """
    Analyzes a user's accomplishment, extracts skills, and updates the knowledge graph.
    - Creates an Accomplishment node and links it to the user.
    - Extracts skills and mastery levels using an LLM from the accomplishment's description.
    - Compares extracted skills against existing skills in the graph to avoid duplicates.
    - Creates new skill nodes for non-duplicate skills (including default mastery levels).
    - Links the newly created accomplishment to each relevant skill.
    """
    try:
        # Step 0: Validate user exists
        with driver.session() as session:
            if not session.read_transaction(graph_crud.user_exists, current_user.email):
                raise HTTPException(status_code=404, detail=f"User with email {current_user.email} not found.")

        # Step 1: Create the Accomplishment node and link it to the user
        with driver.session() as session:
            accomplishment_payload = accomplishment_data.model_dump(exclude_unset=True)
            quest_id = accomplishment_payload.pop("quest_id", None) # Extract quest_id

            accomplishment_node = session.write_transaction(
                graph_crud.create_accomplishment,
                current_user, # Pass the entire User object
                accomplishment_payload,  # Send the dict without quest_id
                quest_id=quest_id # Pass quest_id separately
            )
            # Convert Neo4j Node to Pydantic model.
            # The accomplishment_node from graph_crud doesn't have user_email directly.
            # We need to construct a dictionary for validation, including the user_email from the current session.
            accomplishment_data_for_validation = dict(accomplishment_node) # Convert node to dict
            accomplishment_data_for_validation['user_email'] = current_user.email
            # quest_id might also be needed if it's part of AccomplishmentSchema and not on the node
            if quest_id: # If a quest_id was processed
                accomplishment_data_for_validation['quest_id'] = quest_id

            created_accomplishment = AccomplishmentSchema.model_validate(
                accomplishment_data_for_validation
            )

        # Step 2: Extract skills from the accomplishment description
        extracted_data = await skill_extractor_chain.ainvoke(
            {"accomplishment": accomplishment_data.description}
        )
        extracted_skills = extracted_data.skills

        if not extracted_skills:
            return AccomplishmentResponse(
                message="No skills were extracted from the accomplishment. Accomplishment created.",
                accomplishment=created_accomplishment,
            )

        # Step 3: Get all existing skill names from the database
        with driver.session() as session:
            existing_skill_names = session.read_transaction(graph_crud.get_all_skills)

        final_skill_names_to_link = (
            []
        )  # Store names of skills to be linked to the accomplishment
        processed_skills_for_response = []  # Store SkillLevel objects for the response

        for skill_level in extracted_skills:
            candidate_skill_name = skill_level.skill

            # Step 4: Check for duplicate skills using AI skill matcher
            match_result = await find_skill_match(
                candidate_skill_name, existing_skill_names
            )

            final_skill_name = ""
            if match_result.is_duplicate:
                # Step 5a: If it's a duplicate, use the existing skill name
                final_skill_name = match_result.existing_skill_name
                print(
                    f"Match found for '{candidate_skill_name}': using existing skill '{final_skill_name}'"
                )
            else:
                # Step 5b: If it's new, use the candidate name and create it in the DB
                final_skill_name = candidate_skill_name
                print(f"New skill found: '{final_skill_name}'. Creating in graph...")
                with driver.session() as session:
                    session.write_transaction(graph_crud.create_skill, final_skill_name)
                # Add the new skill to our list of existing skills for the current processing run
                existing_skill_names.append(final_skill_name)

            final_skill_names_to_link.append(final_skill_name)
            # We store the original skill_level (which includes AI's mastery assessment) for the response
            processed_skills_for_response.append(skill_level)

        # Step 6: Link the newly created accomplishment to each relevant skill
        with driver.session() as session:
            for skill_name_to_link in final_skill_names_to_link:
                session.write_transaction(
                    graph_crud.link_accomplishment_to_skill,
                    str(created_accomplishment.id),  # Ensure ID is a string
                    skill_name_to_link,
                )

        # Step 7: If the accomplishment is for a quest, advance the goal
        if created_accomplishment.quest_id:
            with driver.session() as session:
                session.write_transaction(
                    graph_crud.advance_goal,
                    str(created_accomplishment.quest_id),
                    current_user.email,
                )

        return AccomplishmentResponse(
            message=f"Successfully processed accomplishment, created node '{created_accomplishment.name}', and linked {len(final_skill_names_to_link)} skills.",
            accomplishment=created_accomplishment,
        )

    except HTTPException:
        # Re-raise HTTPException instances directly so FastAPI can handle them
        raise
    except Exception as e:
        # Catch all other unexpected errors and return a 500
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred during accomplishment processing: {str(e)}",
        )


@router.post(
    "/accomplishments/{accomplishment_id}/issue-credential",
    tags=["Accomplishments", "VC"],
)
def issue_accomplishment_credential(
    accomplishment_id: uuid.UUID, driver: Driver = Depends(get_graph_db_driver)
):
    """
    Issues a signed Verifiable Credential (in JWT format) for a specific
    verified accomplishment.
    """
    # Use an environment variable for the path, defaulting to the local file
    key_path = os.getenv("PRIVATE_KEY_PATH", "private_key.json")

    # 1. Load the issuer's private key
    try:
        with open(key_path, "r") as f:
            private_key_data = json.load(f)
        issuer_key = jwk.JWK(**private_key_data)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail=f"Issuer key not found at path: {key_path}")

    # 2. Fetch accomplishment details from the graph
    with driver.session() as session:
        accomplishment = session.read_transaction(
            graph_crud.get_accomplishment_details, accomplishment_id
        )
    if not accomplishment:
        raise HTTPException(status_code=404, detail="Accomplishment not found.")

    # 3. Construct the VC Payload
    issuance_date = datetime.datetime.now(datetime.timezone.utc)

    accomplishment_node_data = accomplishment["accomplishment"]
    user_node_data = accomplishment["user"]

    # Ensure timestamp exists and convert it
    achieved_on_iso = None
    if accomplishment_node_data["timestamp"]:
        # Neo4j DateTime objects need conversion to Python native datetime
        achieved_on_iso = accomplishment_node_data["timestamp"].to_native().isoformat()
    else:
        # Handle cases where timestamp might be unexpectedly missing
        raise HTTPException(status_code=500, detail="Accomplishment timestamp is missing.")

    vc_payload = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "id": f"urn:uuid:{uuid.uuid4()}",
        "type": ["VerifiableCredential", "SkillForgeAccomplishment"],
        "issuer": "https://skillforge.io",  # SkillForge's identifier
        "issuanceDate": issuance_date.isoformat(),
        "credentialSubject": {
            # Use email as a more reliable user identifier from the graph node
            "id": str(user_node_data["email"]),
            "accomplishment": {
                "name": accomplishment_node_data["name"],
                "description": accomplishment_node_data["description"],
                "achievedOn": achieved_on_iso,
            },
        },
    }

    # 4. Construct the JWT Claims, placing the VC inside the 'vc' claim
    jwt_claims = {
        "iss": "https://skillforge.io",  # Issuer of the JWT
        # Use email for subject claim as it's guaranteed on the User graph node
        "sub": str(user_node_data["email"]),
        "iat": int(issuance_date.timestamp()),  # Issued at time
        "vc": vc_payload,
    }

    # NEW STEP: Store the VC in the graph *before* returning
    # The vc_payload corresponds to the vc_json in the original problem description
    with driver.session() as session:
        session.write_transaction(
            graph_crud.store_vc_receipt, # Assuming store_vc_receipt is the correct function to store the VC payload
            accomplishment_id,
            vc_payload # Storing the full VC payload as vc_json
        )

    # 5. Sign the JWT with the private key
    signed_vc_jwt = jwt.encode(
        claims=jwt_claims,
        key=issuer_key.export_to_pem(private_key=True, password=None),
        algorithm="ES256",
    )

    return {"verifiable_credential_jwt": signed_vc_jwt}
