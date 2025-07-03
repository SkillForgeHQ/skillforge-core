from pydantic import BaseModel, Field
from typing import List, Optional


class SubTask(BaseModel):
    title: str = Field(description="The concise title of the sub-task.")
    description: str = Field(
        description="A detailed, step-by-step description of how to complete the sub-task."
    )
    duration_minutes: int = Field(
        description="The estimated time in minutes to complete the sub-task."
    )


class ParsedGoal(BaseModel):
    goal_title: str = Field(
        description="A clear, re-stated title for the overall goal."
    )
    sub_tasks: List[SubTask] = Field(
        description="A list of detailed, actionable sub-tasks to achieve the goal."
    )


class SkillLevel(BaseModel):
    skill: str = Field(description="The name of a single, specific skill.")
    level: str = Field(
        description="The mastery level demonstrated, e.g., 'Beginner', 'Intermediate', 'Advanced', or 'Expert'."
    )


class ExtractedSkills(BaseModel):
    skills: List[SkillLevel] = Field(
        description="A list of skills and the mastery levels demonstrated."
    )


class SkillMatch(BaseModel):
    is_duplicate: bool = Field(
        description="A boolean flag indicating if the candidate skill is a duplicate of an existing skill."
    )
    existing_skill_name: Optional[str] = Field(
        description="If is_duplicate is true, this is the name of the existing skill that matches."
    )


class UserPasswordChange(BaseModel):
    current_password: str
    new_password: str
