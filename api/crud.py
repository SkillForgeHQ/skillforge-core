# api/crud.py

from sqlalchemy import select, insert
from sqlalchemy.engine import Connection
from . import database, schemas
from .security import get_password_hash

# We use the SQLAlchemy table object defined in database.py
skills_table = database.skills

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
