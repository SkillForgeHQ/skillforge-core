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
