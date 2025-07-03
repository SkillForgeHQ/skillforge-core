from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from neo4j import Driver
from ..ai.parser import goal_parser_chain
from ..ai.schemas import ParsedGoal, SkillLevel
from ..ai.skill_extractor import skill_extractor_chain
from ..ai.skill_matcher import find_skill_match

# Database Imports
from ..database import get_graph_db_driver
from .. import accomplishment_crud

# Security Imports
from .auth import get_current_user
from ..schemas import User

router = APIRouter()


class GoalRequest(BaseModel):
    goal: str


@router.post("/goals/parse", response_model=ParsedGoal, tags=["AI"])
async def parse_goal_into_subtasks(request: GoalRequest):
    """
    Accepts a high-level goal and uses an LLM to break it down into
    a structured list of sub-tasks.
    """
    try:
        # Invoke the LangChain chain with the user's goal
        parsed_result = await goal_parser_chain.ainvoke({"goal": request.goal})
        return parsed_result
    except Exception as e:
        # Handle potential parsing errors or API failures
        raise HTTPException(status_code=500, detail=f"Failed to parse goal: {str(e)}")


class AccomplishmentRequest(BaseModel):
    accomplishment: str


class AccomplishmentResponse(BaseModel):
    message: str
    processed_skills: List[SkillLevel]


@router.post(
    "/accomplishments/process",
    response_model=AccomplishmentResponse,
    tags=["Accomplishments"],
)
async def process_accomplishment(
    request: AccomplishmentRequest,
    driver: Driver = Depends(get_graph_db_driver),
    current_user: User = Depends(get_current_user),
):
    """
    Analyzes a user's accomplishment, extracts skills, and updates the knowledge graph.
    - Extracts skills and mastery levels using an LLM.
    - Compares extracted skills against existing skills in the graph to avoid duplicates.
    - Creates new skill nodes for non-duplicate skills.
    - Assigns mastery of each skill to the current user.
    """
    try:
        # 1. Extract skills from the accomplishment text using our first AI chain
        extracted_data = await skill_extractor_chain.ainvoke(
            {"accomplishment": request.accomplishment}
        )
        extracted_skills = extracted_data.skills

        if not extracted_skills:
            return {
                "message": "No skills were extracted from the accomplishment.",
                "processed_skills": [],
            }

        # 2. Get all existing skill names from the database
        existing_skill_names = accomplishment_crud.get_all_skill_names(driver)

        processed_skills = []
        for skill_level in extracted_skills:
            candidate_skill_name = skill_level.skill

            # 3. Use our second AI chain to check for duplicates
            match_result = await find_skill_match(
                candidate_skill_name, existing_skill_names
            )

            final_skill_name = ""
            if match_result.is_duplicate:
                # 4a. If it's a duplicate, use the existing skill name
                final_skill_name = match_result.existing_skill_name
                print(
                    f"Match found: '{candidate_skill_name}' is a duplicate of '{final_skill_name}'"
                )
            else:
                # 4b. If it's new, use the candidate name and create it in the DB
                final_skill_name = candidate_skill_name
                print(f"New skill found: '{final_skill_name}'. Creating in graph...")
                accomplishment_crud.add_new_skill_with_masteries(
                    driver, final_skill_name
                )
                # Add the new skill to our list so we don't create it twice in the same run
                existing_skill_names.append(final_skill_name)

            # 5. Assign the final skill and mastery level to the user
            accomplishment_crud.assign_mastery_to_user(
                driver, current_user.email, final_skill_name, skill_level.level
            )
            processed_skills.append(skill_level)

        return {
            "message": f"Successfully processed accomplishment and assigned {len(processed_skills)} skills.",
            "processed_skills": processed_skills,
        }

    except Exception as e:
        # A broad exception handler for any AI or database errors
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
