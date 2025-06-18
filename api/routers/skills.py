# api/routers/skills.py

from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.engine import Connection

from .. import crud, schemas

# CORRECTED: This now points to 'database' instead of 'main'
from ..database import get_db

router = APIRouter()


@router.post("/", response_model=schemas.Skill, status_code=201)
def create_skill(skill: schemas.SkillCreate, db: Connection = Depends(get_db)):
    db_skill = crud.get_skill_by_name(conn=db, name=skill.name)
    if db_skill:
        raise HTTPException(
            status_code=400, detail=f"Skill with name '{skill.name}' already exists."
        )
    return crud.create_skill(conn=db, skill=skill)


@router.get("/", response_model=List[schemas.Skill])
def list_skills(skip: int = 0, limit: int = 100, db: Connection = Depends(get_db)):
    skills = crud.get_all_skills(conn=db, skip=skip, limit=limit)
    return skills


@router.get("/{skill_name}", response_model=schemas.Skill)
def read_skill(skill_name: str, db: Connection = Depends(get_db)):
    db_skill = crud.get_skill_by_name(conn=db, name=skill_name)
    if db_skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return db_skill


@router.put("/{skill_name}", response_model=schemas.Skill)
def update_skill_endpoint(
    skill_name: str, skill: schemas.SkillUpdate, db: Connection = Depends(get_db)
):
    db_skill = crud.get_skill_by_name(conn=db, name=skill_name)
    if db_skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return crud.update_skill(conn=db, name=skill_name, skill=skill)
