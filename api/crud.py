# api/crud.py

from sqlalchemy import select, insert
from sqlalchemy.engine import Connection
from . import database, schemas
from .security import get_password_hash

# We use the SQLAlchemy table object defined in database.py
skills_table = database.skills


def get_skill_by_name(conn: Connection, name: str):
    """Fetches a single skill by its unique name."""
    query = skills_table.select().where(skills_table.c.name == name)
    result = conn.execute(query).first()
    return result


def get_all_skills(conn: Connection, skip: int = 0, limit: int = 100):
    """Fetches all skills with pagination."""
    query = skills_table.select().offset(skip).limit(limit)
    result = conn.execute(query).fetchall()
    return result


def create_skill(conn: Connection, skill: schemas.SkillCreate):
    """Creates a new skill in the database."""
    query = skills_table.insert().values(
        name=skill.name, description=skill.description, dependencies=skill.dependencies
    )
    # Execute the query and return the new record
    result = conn.execute(query)
    conn.commit()  # Commit the transaction to save the data

    # We need to fetch the newly created record to get the db-generated values
    created_skill_pk = result.inserted_primary_key[0]
    return get_skill_by_pk(conn, created_skill_pk)


def get_skill_by_pk(conn: Connection, pk: str):
    """Fetches a single skill by its primary key (UUID)."""
    query = skills_table.select().where(skills_table.c.id == pk)
    result = conn.execute(query).first()
    return result


def update_skill(conn: Connection, name: str, skill: schemas.SkillUpdate):
    """Updates an existing skill."""
    # Create a dictionary of the data to update, excluding any None values
    # so we don't accidentally null out fields.
    update_data = skill.model_dump(exclude_unset=True)

    if update_data:
        query = (
            skills_table.update()
            .where(skills_table.c.name == name)
            .values(**update_data)
        )
        conn.execute(query)
        conn.commit()

    # Return the updated skill record
    return get_skill_by_name(conn, name)


# Add these functions to api/crud.py


def get_user_by_email(conn: Connection, email: str):
    """Fetches a single user by their email address."""
    query = select(database.users).where(database.users.c.email == email)
    result = conn.execute(query).first()
    return result


def create_user(conn: Connection, user: schemas.UserCreate):
    """Creates a new user in the database."""
    # Hash the password from the input schema
    hashed_password = get_password_hash(user.password)

    # Prepare the user data for insertion, excluding the plain password
    user_data = user.model_dump(exclude={"password"})
    user_data["hashed_password"] = hashed_password

    # Create the insert statement and execute it
    query = insert(database.users).values(user_data)
    result = conn.execute(query)

    # Fetch the newly created user to return it
    created_user = get_user_by_email(conn, user.email)
    conn.commit()  # Commit the transaction
    return created_user
