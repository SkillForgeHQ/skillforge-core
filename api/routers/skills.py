# api/routers/skills.py

from fastapi import APIRouter, HTTPException, Depends
from neo4j import Driver
from typing import List
from sqlalchemy.engine import Connection
from ..database import get_graph_db_driver
from .. import crud, schemas, graph_crud
from ..database import get_db
from pydantic import BaseModel

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

@router.get("/graph/test", response_model=List[str])
def get_skill_titles_from_graph(driver: Driver = Depends(get_graph_db_driver)):
    """
    A test endpoint to verify the connection to Neo4j and fetch skill titles.
    """
    records, _, _ = driver.execute_query("MATCH (s:Skill) RETURN s.title AS title")
    return [record["title"] for record in records]

class GraphSkillCreate(BaseModel):
    name: str

@router.post("/graph/skills", status_code=201, tags=["Skills (Neo4j)"])
def create_graph_skill(skill: GraphSkillCreate, driver: Driver = Depends(get_graph_db_driver)):
    """
    Create a new Skill node in the Neo4j graph database.
    """
    with driver.session() as session:
        # Check is skill exists first
        existing_skill = session.execute_read(graph_crud.get_skill_by_name, skill.name)
        if existing_skill:
            raise HTTPException(status_code=409, detail="Skill already exists in the graph")

        #Use the write transaction function from graph_crud.py
        new_skill = session.execute_write(graph_crud.create_skill, skill.name)
        return {"message": "Skill created in graph", "skill": new_skill["name"]}

@router.get("/graph/skills", response_model=List[str], tags=["Skills (Neo4j)"])
def list_graph_skills(driver: Driver = Depends(get_graph_db_driver)):
    """
    Retrieve all skill names from the Neo4j graph database.
    """
    with driver.session() as session:
        # Use the read transaction function from graph_crud.py
        skills = session.execute_read(graph_crud.get_all_skills)
    return skills


# Your existing test endpoint fits perfectly in this pattern
@router.get("/graph/test", response_model=List[str], tags=["Skills (Neo4j)"])
def get_skill_titles_from_graph(driver: Driver = Depends(get_graph_db_driver)):
    records, _, _ = driver.execute_query("MATCH (s:Skill) RETURN s.name AS name")
    return [record["name"] for record in records]


class SkillUpdate(BaseModel):
    new_name: str


# GET A SINGLE SKILL (Read)
@router.get("/graph/skills/{skill_name}", response_model=str, tags=["Skills (Neo4j)"])
def get_graph_skill(skill_name: str, driver: Driver = Depends(get_graph_db_driver)):
    """
    Retrieve a single skill by name from the graph.
    """
    with driver.session() as session:
        skill = session.execute_read(graph_crud.get_skill_by_name, skill_name)
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found in graph")
    return skill["name"]


# UPDATE A SKILL (Update)
@router.put("/graph/skills/{skill_name}", response_model=str, tags=["Skills (Neo4j)"])
def update_graph_skill(skill_name: str, skill_update: SkillUpdate, driver: Driver = Depends(get_graph_db_driver)):
    """
    Update a skill's name in the graph.
    """
    with driver.session() as session:
        # First, check if the skill to update even exists
        existing_skill = session.execute_read(graph_crud.get_skill_by_name, skill_name)
        if not existing_skill:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

        # Now, perform the update
        updated_skill = session.execute_write(graph_crud.update_skill, skill_name, skill_update.new_name)
        return updated_skill["name"]


# DELETE A SKILL (Delete)
@router.delete("/graph/skills/{skill_name}", status_code=200, tags=["Skills (Neo4j)"])
def delete_graph_skill(skill_name: str, driver: Driver = Depends(get_graph_db_driver)):
    """
    Delete a skill from the graph.
    """
    with driver.session() as session:
        # Check if the skill exists before trying to delete it
        existing_skill = session.execute_read(graph_crud.get_skill_by_name, skill_name)
        if not existing_skill:
            raise HTTPException(status_code=404, detail="Skill not found in graph")

        # Perform the deletion
        session.execute_write(graph_crud.delete_skill, skill_name)
        return {"message": f"Skill '{skill_name}' deleted successfully"}