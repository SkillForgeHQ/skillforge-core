# api/crud.py

from sqlalchemy import select, insert, update
from sqlalchemy.engine import Connection
from . import database, schemas, security
from .security import get_password_hash

# We use the SQLAlchemy table object defined in database.py


def get_user_by_email(conn: Connection, email: str):
    """Fetches a single user by their email address."""
    query = select(database.users).where(database.users.c.email == email)
    result = conn.execute(query).first()
    return result


def create_user(conn: Connection, user: schemas.UserCreate):
    """Creates a new user in the database."""
    hashed_password = security.get_password_hash(user.password)
    user_data = {
        "email": user.email,
        "hashed_password": hashed_password
    }

    # Using .returning() is more efficient to get the new user's data back
    stmt = insert(database.users).values(user_data).returning(database.users)

    result = conn.execute(stmt).first()
    conn.commit()  # Commit the transaction
    return result


def update_user_password(db: Connection, user_email: str, new_hashed_password: str):
    """
    Updates a user's password in the database.
    """
    stmt = (
        update(database.users)
        .where(database.users.c.email == user_email)
        .values(hashed_password=new_hashed_password)
    )
    db.execute(stmt)
    db.commit()
