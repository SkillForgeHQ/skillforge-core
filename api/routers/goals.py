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
from .. import graph_crud # Added for Quest creation
from ..schemas import Quest as QuestSchema # Added for response model

# Security Imports
from .auth import get_current_user
from ..schemas import User

router = APIRouter()


class GoalRequest(BaseModel):
    goal: str


@router.post("/goals/parse", response_model=ParsedGoal, tags=["AI", "Goals"]) # Corrected tags
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


class PersonalizedPathRequest(BaseModel):
    goal_description: str
    # user_id: str # Assuming user context will be handled by auth


@router.post("/goals/personalized-path", response_model=QuestSchema, tags=["AI", "Goals"])
async def get_personalized_path(
    request: PersonalizedPathRequest,
    db: Driver = Depends(get_graph_db_driver),
    current_user: User = Depends(get_current_user),
):
    """
    Generates a personalized quest based on the user's goal,
    stores it in the graph, and returns the quest.
    """
    # This is a placeholder for where the LLM would generate the quest suggestion
    # In a real scenario, you would invoke a LangChain or similar LLM call here
    # using request.goal_description and potentially user's existing skills/accomplishments.
    # For now, we'll use a simplified version.

    # Simulate LLM generating quest text
    quest_suggestion_text = f"Based on your goal '{request.goal_description}', a good first step would be to learn about its core concepts and create a small project. User: {current_user.email}"

    # Create the Quest in the graph
    quest_data = {
        "name": f"Personalized Quest for {current_user.email}", # Consider parsing a title from the LLM
        "description": quest_suggestion_text
    }
    with db.session() as session:
        new_quest_node = session.write_transaction(graph_crud.create_quest, quest_data)
        # Convert Neo4j Node to Pydantic model.
        # Assuming your Quest Pydantic model can handle a Neo4j Node.
        # If not, you might need to manually construct the Pydantic model
        # from the node properties. For this example, we'll assume model_validate works.
        # You may need to adjust this based on how create_quest returns data
        # and how your Quest schema is set up for Neo4j node validation.
        # If create_quest returns a dict-like structure or specific properties:
        new_quest = QuestSchema.model_validate(new_quest_node)


    return new_quest # Return the full Quest object
