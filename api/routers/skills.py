from pydantic import BaseModel
from typing import List, Optional
from fastapi import APIRouter, HTTPException

router = APIRouter()

fake_db = {
    "python-basics": {
        "skill_id": "python-basics",
        "name": "Python Basics",
        "description": "Fundamental concepts of Python programming.",
        "dependencies": []
    }
}

class Skill(BaseModel):
    skill_id: str
    name: str
    description: Optional[str] = None
    dependencies: List[str] = []

@router.get('/{skill_id}', response_model=Skill)
async def read_skill(skill_id: str):
    if skill_id not in fake_db:
        raise HTTPException(status_code=404, detail="Skill not found")
    return fake_db[skill_id]

@router.post('/', response_model=Skill)
async def create_skill(skill: Skill):
    global fake_db
    if skill.skill_id in fake_db:
        raise HTTPException(status_code=400, detail="Skill ID already exists")
    fake_db[skill.skill_id] = skill.model_dump()
    return skill