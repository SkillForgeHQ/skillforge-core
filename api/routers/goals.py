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


@router.post("/goals/parse", response_model=schemas.GoalAndQuest, tags=["AI"])
async def parse_goal_into_subtasks(
    request: GoalRequest,
    db: Neo4jSession = Depends(get_graph_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Accepts a high-level goal, breaks it down into sub-tasks, creates a :Goal node
    with the full plan, and creates the first sub-task as a :Quest node.
    """
    try:
        parsed_result: ParsedGoal = await goal_parser_chain.ainvoke({"goal": request.goal})

        if not parsed_result or not parsed_result.sub_tasks:
            raise HTTPException(status_code=400, detail="Could not parse the goal into sub-tasks.")

        import json
        full_plan_json = json.dumps([sub_task.dict() for sub_task in parsed_result.sub_tasks])

        goal_data = schemas.GoalCreate(
            goal_text=request.goal,
            full_plan_json=full_plan_json
        )

        # This transaction creates the goal and the first quest
        def create_goal_and_first_quest(tx, goal_data, user_email):
            # Create the Goal node
            goal_node = graph_crud.create_goal_and_link_to_user(tx, goal_data, user_email)

            # Create the first Quest from the plan
            first_sub_task = parsed_result.sub_tasks[0]
            quest_data = {
                "name": first_sub_task.title,
                "description": first_sub_task.description
            }
            first_quest_node = graph_crud.create_quest_and_link_to_user(tx, quest_data, user_email)

            # Link Goal to the first Quest as the active quest
            link_query = """
            MATCH (g:Goal {id: $goal_id})
            MATCH (q:Quest {id: $quest_id})
            CREATE (g)-[:HAS_ACTIVE_QUEST]->(q)
            """
            tx.run(link_query, goal_id=goal_node['id'], quest_id=first_quest_node['id'])

            return goal_node, first_quest_node

        # Execute the transaction
        goal_node, first_quest = db.write_transaction(
            create_goal_and_first_quest,
            goal_data,
            current_user.email
        )

        goal_model = schemas.Goal.model_validate(dict(goal_node))
        quest_model = schemas.Quest.model_validate(dict(first_quest))

        return {"goal": goal_model, "quest": quest_model}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process goal: {str(e)}")
