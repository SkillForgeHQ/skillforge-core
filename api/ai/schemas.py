from pydantic import BaseModel, Field
from typing import List

class SubTask(BaseModel):
    title: str = Field(description="The concise title of the sub-task.")
    description: str = Field(description="A detailed, step-by-step description of how to complete the sub-task.")
    duration_minutes: int = Field(description="The estimated time in minutes to complete the sub-task.")

class ParsedGoal(BaseModel):
    goal_title: str = Field(description="A clear, re-stated title for the overall goal.")
    sub_tasks: List[SubTask] = Field(description="A list of detailed, actionable sub-tasks to achieve the goal.")