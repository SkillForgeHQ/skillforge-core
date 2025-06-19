# api/database.py

import os
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    String,
    Text,
    func,
    TIMESTAMP,
    Integer,
    Boolean
)
from sqlalchemy.engine import Connection
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = (
    f"postgresql+psycopg://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

engine = create_engine(DATABASE_URL)
metadata = MetaData()

skills = Table(
    "skills",
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    ),
    Column("name", String(255), nullable=False, unique=True),
    Column("description", Text),
    Column("dependencies", ARRAY(String)),
    Column(
        "created_at",
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
    # CORRECTED: Added nullable=False
    Column(
        "updated_at",
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),
)

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("email", String, unique=True, index=True),
    Column("hashed_password", String, nullable=False), # Added nullable=False
    Column("is_active", Boolean, default=True),
)

def get_db() -> Connection:
    conn = engine.connect()
    try:
        yield conn
    finally:
        conn.close()
