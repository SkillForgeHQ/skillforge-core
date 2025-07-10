from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from neo4j import Session as Neo4jSession # Changed Driver to Session
from ..ai.parser import goal_parser_chain
# ParsedGoal is no longer the direct response_model, but its structure is used
from ..ai.schemas import ParsedGoal, SubTask

# Database Imports
from ..database import get_graph_db_session # Changed to get_graph_db_session
from .. import graph_crud # Added graph_crud import
from .. import schemas # Added schemas import for response_model

# Security Imports
from .auth import get_current_user # Not used in this specific function currently
from ..schemas import User # Not used in this specific function currently

router = APIRouter()


class GoalRequest(BaseModel):
    goal: str


@router.post("/goals/parse", response_model=List[schemas.Quest], tags=["AI"]) # Changed response_model
async def parse_goal_into_subtasks(
    request: GoalRequest,
    db: Neo4jSession = Depends(get_graph_db_session), # Added db session dependency
    current_user: User = Depends(get_current_user)
):
    """
    Accepts a high-level goal, uses an LLM to break it down into
    a structured list of sub-tasks, creates a Quest node for each sub-task,
    and returns the list of created Quests.
    """
    try:
        # Invoke the LangChain chain with the user's goal
        # parsed_result will be of type ParsedGoal
        parsed_result: ParsedGoal = await goal_parser_chain.ainvoke({"goal": request.goal})

        created_quests: List[schemas.Quest] = []
        if parsed_result and parsed_result.sub_tasks:
            for sub_task in parsed_result.sub_tasks:
                quest_data = {
                    "name": sub_task.title, # Using title from SubTask
                    "description": sub_task.description # Using description from SubTask
                }
                # Create a Quest node in the graph for each sub-task
                # and link it to the current user.
                # graph_crud.create_quest_and_link_to_user will be implemented next
                # and is expected to return a Neo4j Node object.
                new_quest_node = db.write_transaction(
                    graph_crud.create_quest_and_link_to_user, quest_data, current_user.email
                )
                # FastAPI will automatically convert the Node to schemas.Quest
                # due to model_config = {"from_attributes": True} in schemas.Quest
                created_quests.append(new_quest_node)

        return created_quests
    except Exception as e:
        # Handle potential parsing errors or API failures
        raise HTTPException(status_code=500, detail=f"Failed to parse goal and create quests: {str(e)}")
