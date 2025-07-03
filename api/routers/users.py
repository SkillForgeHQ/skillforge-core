# api/routers/users.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Connection
from neo4j import Driver
from .. import crud, schemas, graph_crud, security
from ..database import get_db, get_graph_db_driver
from .auth import get_current_active_user
from typing import List
from ..routers.auth import get_current_user

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


@router.post("/", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UserCreate, conn: Connection = Depends(get_db)):
    """
    Register a new user.
    """
    db_user = crud.get_user_by_email(conn=conn, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    created_user = crud.create_user(conn=conn, user=user)
    return created_user


@router.get("/me", response_model=schemas.User)
def read_users_me(current_user: schemas.User = Depends(get_current_user)):
    """
    Fetch the currently logged-in user.
    """
    return current_user


@router.post("/graph/users/{email}", status_code=201, tags=["Users (Neo4j)"])
def create_graph_user(email: str, driver: Driver = Depends(get_graph_db_driver)):
    """
    Create a new User node in the graph.
    """
    with driver.session() as session:
        user_email = session.execute_write(graph_crud.create_user_node, email)
    return {"message": "User created in graph", "email": user_email}


@router.post("/{email}/skills", status_code=201, tags=["Users (Neo4j)"])
def set_skill_mastery_for_user(
    email: str,
    mastery_info: schemas.UserSkillMasteryCreate,
    driver: Driver = Depends(get_graph_db_driver)
):
    """
    Sets or updates a user's mastery level for a specific skill.
    This replaces the simple "add skill" functionality.
    """
    with driver.session() as session:
        # Check if user and skill exist
        user_node = session.execute_read(graph_crud.get_user_by_email, email) # Assuming you create a graph_crud version for this
        if not user_node:
            raise HTTPException(status_code=404, detail=f"User '{email}' not found.")

        skill_node = session.execute_read(graph_crud.get_skill_by_name, mastery_info.skill_name)
        if not skill_node:
            raise HTTPException(status_code=404, detail=f"Skill '{mastery_info.skill_name}' not found.")

        # Set the mastery level
        result = session.execute_write(
            graph_crud.set_user_skill_mastery,
            email,
            mastery_info.skill_name,
            mastery_info.mastery_level
        )

        if not result:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to set mastery. Ensure mastery level {mastery_info.mastery_level} exists for skill '{mastery_info.skill_name}'."
            )

    return {
        "message": f"User '{email}' now has mastery level {result['level']} of skill '{result['skill']}'"
    }


@router.get(
    "/graph/users/{email}/learning-path/{skill_name}",
    response_model=List[str],
    tags=["Users (Neo4j)"],
)
def get_personalized_path(
    email: str, skill_name: str, driver: Driver = Depends(get_graph_db_driver)
):
    """
    Generates a personalized learning path for a user,
    excluding skills they already possess.
    """
    with driver.session() as session:
        # 1. Get the complete, ideal learning path
        full_path = session.execute_read(
            graph_crud.get_consolidated_learning_path, skill_name
        )

        # 2. Get the skills the user already has
        user_skills = session.execute_read(graph_crud.get_user_skills, email)

    # 3. In Python, filter the full path to exclude skills the user has
    # We use a set for user_skills for a more efficient lookup.
    user_skills_set = set(user_skills)
    personalized_path = [skill for skill in full_path if skill not in user_skills_set]

    if not full_path:
        raise HTTPException(
            status_code=404, detail=f"No learning path found for skill '{skill_name}'."
        )

    return personalized_path


@router.delete(
    "/graph/users/{email}/skills/{skill_name}", status_code=200, tags=["Users (Neo4j)"]
)
def remove_skill_from_user(
    email: str, skill_name: str, driver: Driver = Depends(get_graph_db_driver)
):
    """
    Removes a skill from a user's profile by deleting the :HAS_SKILL relationship.
    """
    with driver.session() as session:
        # You might add logic here to check if the user and skill exist first
        session.execute_write(graph_crud.remove_user_skill, email, skill_name)
    return {"message": f"Skill '{skill_name}' removed from user '{email}'"}

@router.put("/users/me/password", status_code=status.HTTP_204_NO_CONTENT, tags=["Users"])
def change_current_user_password(
    password_data: schemas.UserPasswordChange,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Connection = Depends(get_db)
):
    """
    Allows an authenticated user to change their own password.
    """
    # 1. Verify the user's current password
    user_in_db = crud.get_user(db, email=current_user.email)
    if not security.verify_password(password_data.current_password, user_in_db.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password",
        )

    # 2. Hash the new password
    new_hashed_password = security.get_password_hash(password_data.new_password)

    # 3. Update the password in the database
    crud.update_user_password(db, email=current_user.email, new_hashed_password=new_hashed_password)

    return