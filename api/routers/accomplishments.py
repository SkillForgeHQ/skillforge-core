from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from neo4j import Driver
import json
import datetime
import uuid
import os

from ..ai.schemas import SkillLevel
from ..ai.skill_extractor import skill_extractor_chain
from ..ai.skill_matcher import find_skill_match
from ..database import get_graph_db_driver
from .. import graph_crud
from ..schemas import AccomplishmentCreate, Accomplishment as AccomplishmentSchema, User
from .auth import get_current_user
from jwcrypto import jwk
from jose import jwt


router = APIRouter()


class AccomplishmentResponse(BaseModel):
    message: str
    accomplishment: AccomplishmentSchema
    processed_skills: List[SkillLevel]


@router.post(
    "/process",
    response_model=AccomplishmentResponse,
    tags=["Accomplishments"],
)
async def process_accomplishment(
    accomplishment_data: AccomplishmentCreate,
    driver: Driver = Depends(get_graph_db_driver),
    current_user: User = Depends(get_current_user),
):
    """
    Analyzes a user's accomplishment, extracts skills, and updates the knowledge graph.
    The user is identified SOLELY by the authentication token.
    """
    try:
        # Step 0: Validate that the authenticated user actually exists in the graph.
        with driver.session() as session:
            if not session.execute_read(graph_crud.user_exists, current_user.email):
                raise HTTPException(
                    status_code=404,
                    detail=f"User with email '{current_user.email}' not found."
                )

        # Step 1: Create the Accomplishment node
        with driver.session() as session:
            accomplishment_payload = accomplishment_data.model_dump(exclude_unset=True)
            quest_id = accomplishment_payload.pop("quest_id", None)

            accomplishment_node = session.execute_write(
                graph_crud.create_accomplishment,
                current_user.email,
                accomplishment_payload,
                quest_id=quest_id,
            )
            created_accomplishment = AccomplishmentSchema.model_validate(accomplishment_node)

        # ... (rest of the function remains the same) ...
        # Step 2: Extract skills
        extracted_data = await skill_extractor_chain.ainvoke(
            {"accomplishment": accomplishment_data.description}
        )
        extracted_skills = extracted_data.skills

        if not extracted_skills:
            return AccomplishmentResponse(
                message="Accomplishment created, but no skills were extracted.",
                accomplishment=created_accomplishment,
                processed_skills=[],
            )

        # Step 3: Deduplicate and process skills
        with driver.session() as session:
            existing_skill_names = session.execute_read(graph_crud.get_all_skills)

        final_skill_names_to_link = []
        for skill_level in extracted_skills:
            match_result = await find_skill_match(skill_level.skill, existing_skill_names)
            final_skill_name = match_result.existing_skill_name if match_result.is_duplicate else skill_level.skill

            if not match_result.is_duplicate:
                with driver.session() as session:
                    session.execute_write(graph_crud.create_skill, final_skill_name)
                existing_skill_names.append(final_skill_name)

            final_skill_names_to_link.append(final_skill_name)

        # Step 4: Link accomplishment to skills
        with driver.session() as session:
            for skill_name in final_skill_names_to_link:
                session.execute_write(
                    graph_crud.link_accomplishment_to_skill,
                    str(created_accomplishment.id),
                    skill_name,
                )

        return AccomplishmentResponse(
            message=f"Successfully processed accomplishment and linked {len(final_skill_names_to_link)} skills.",
            accomplishment=created_accomplishment,
            processed_skills=extracted_skills,
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}",
        )


@router.post(
    "/{accomplishment_id}/issue-credential",
    tags=["Accomplishments", "VC"],
)
def issue_accomplishment_credential(
    accomplishment_id: uuid.UUID, driver: Driver = Depends(get_graph_db_driver)
):
    """
    Issues a signed Verifiable Credential (in JWT format) for an accomplishment.
    """
    key_path = os.getenv("PRIVATE_KEY_PATH", "private_key.json")
    try:
        with open(key_path, "r") as f:
            private_key_data = json.load(f)
        issuer_key = jwk.JWK(**private_key_data)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail=f"Issuer key not found at path: {key_path}")

    with driver.session() as session:
        accomplishment = session.execute_read(graph_crud.get_accomplishment_details, accomplishment_id)
    if not accomplishment:
        raise HTTPException(status_code=404, detail="Accomplishment not found.")

    issuance_date = datetime.datetime.now(datetime.timezone.utc)
    achieved_on_iso = accomplishment["accomplishment"]["timestamp"].to_native().isoformat()

    vc_payload = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "id": f"urn:uuid:{uuid.uuid4()}",
        "type": ["VerifiableCredential", "SkillForgeAccomplishment"],
        "issuer": "https://skillforge.io",
        "issuanceDate": issuance_date.isoformat(),
        "credentialSubject": {
            "id": str(accomplishment["user"]["email"]),
            "accomplishment": {
                "name": accomplishment["accomplishment"]["name"],
                "description": accomplishment["accomplishment"]["description"],
                "achievedOn": achieved_on_iso,
            },
        },
    }

    jwt_claims = {
        "iss": "https://skillforge.io",
        "sub": str(accomplishment["user"]["email"]),
        "iat": int(issuance_date.timestamp()),
        "vc": vc_payload,
    }

    with driver.session() as session:
        session.execute_write(
            graph_crud.store_vc_receipt,
            accomplishment_id,
            {"id": vc_payload["id"], "issuanceDate": vc_payload["issuanceDate"]},
        )

    signed_vc_jwt = jwt.encode(
        claims=jwt_claims,
        key=issuer_key.export_to_pem(private_key=True, password=None),
        algorithm="ES256",
    )
    return {"verifiable_credential_jwt": signed_vc_jwt}
