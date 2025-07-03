from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..ai.parser import goal_parser_chain
from ..ai.schemas import ParsedGoal

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