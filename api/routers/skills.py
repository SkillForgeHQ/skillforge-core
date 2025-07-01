# api/routers/skills.py

from fastapi import APIRouter, HTTPException, Depends
from neo4j import Driver
from typing import List
from sqlalchemy.engine import Connection
from pydantic import BaseModel

from ..database import get_graph_db_driver, get_db
from .. import crud, schemas, graph_crud


# --- Pydantic Models ---

class GraphSkillCreate(BaseModel):
    name: str

class SkillUpdate(BaseModel):
    new_name: str


# --- Router ---

router = APIRouter()


# --- SQLAlchemy Endpoints (PostgreSQL) ---

@router.post("/", response_model=schemas.Skill, status_code=201, tags=["Skills (PostgreSQL)"])
def create_skill(skill: schemas.SkillCreate, db: Connection = Depends(get_db)):
    db_skill = crud.get_skill_by_name(conn=db, name=skill.name)
    if db_skill:
        raise HTTPException(
            status_code=400, detail=f"Skill with name '{skill.name}' already exists."
        )
    return crud.create_skill(conn=db, skill=skill)


@router.get("/", response_model=List[schemas.Skill], tags=["Skills (PostgreSQL)"])
def list_skills(skip: int = 0, limit: int = 100, db: Connection = Depends(get_db)):
    skills = crud.get_all_skills(conn=db, skip=skip, limit=limit)
    return skills


@router.get("/{skill_name}", response_model=schemas.Skill, tags=["Skills (PostgreSQL)"])
def read_skill(skill_name: str, db: Connection = Depends(get_db)):
    db_skill = crud.get_skill_by_name(conn=db, name=skill_name)
    if db_skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return db_skill


@router.put("/{skill_name}", response_model=schemas.Skill, tags=["Skills (PostgreSQL)"])
def update_skill_endpoint(
    skill_name: str, skill: schemas.SkillUpdate, db: Connection = Depends(get_db)
):
    db_skill = crud.get_skill_by_name(conn=db, name=skill_name)
    if db_skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return crud.update_skill(conn=db, name=skill_name, skill=skill)


# --- Graph Endpoints (Neo4j) ---

@router.post("/graph/skills", status_code=201, tags=["Skills (Neo4j)"])
def create_graph_skill(skill: GraphSkillCreate, driver: Driver = Depends(get_graph_db_driver)):
    """
    Create a new Skill node in the Neo4j graph database.
    """
    with driver.session() as session:
        existing_skill = session.execute_read(graph_crud.get_skill_by_name, skill.name)
        if existing_skill:
            raise HTTPException(status_code=409, detail="Skill already exists in the graph")

        new_skill = session.execute_write(graph_crud.create_skill, skill.name)
        return {"message": "Skill created in graph", "skill": new_skill["name"]}


@router.get("/graph/skills", response_model=List[str], tags=["Skills (Neo4j)"])
def list_graph_skills(driver: Driver = Depends(get_graph_db_driver)):
    """
    Retrieve all skill names from the Neo4j graph database.
    """
    with driver.session() as session:
        skills = session.execute_read(graph_crud.get_all_skills)
    return skills


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


@router.put("/graph/skills/{skill_name}", response_model=str, tags=["Skills (Neo4j)"])
def update_graph_skill(skill_name: str, skill_update: SkillUpdate, driver: Driver = Depends(get_graph_db_driver)):
    """
    Update a skill's name in the graph.
    """
    with driver.session() as session:
        existing_skill = session.execute_read(graph_crud.get_skill_by_name, skill_name)
        if not existing_skill:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

        updated_skill = session.execute_write(graph_crud.update_skill, skill_name, skill_update.new_name)
        return updated_skill["name"]


@router.delete("/graph/skills/{skill_name}", status_code=200, tags=["Skills (Neo4j)"])
def delete_graph_skill(skill_name: str, driver: Driver = Depends(get_graph_db_driver)):
    """
    Delete a skill from the graph.
    """
    with driver.session() as session:
        existing_skill = session.execute_read(graph_crud.get_skill_by_name, skill_name)
        if not existing_skill:
            raise HTTPException(status_code=404, detail="Skill not found in graph")

        session.execute_write(graph_crud.delete_skill, skill_name)
        return {"message": f"Skill '{skill_name}' deleted successfully"}


@router.get("/graph/test", response_model=List[str], tags=["Skills (Neo4j)"])
def get_skill_titles_from_graph(driver: Driver = Depends(get_graph_db_driver)):
    """
    A test endpoint to verify the connection to Neo4j and fetch skill names.
    """
    records, _, _ = driver.execute_query("MATCH (s:Skill) RETURN s.name AS name")
    return [record["name"] for record in records]