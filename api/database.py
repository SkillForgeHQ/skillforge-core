# api/database.py

import os
from pathlib import Path
from dotenv import load_dotenv

# --- This block now correctly loads the .env file ---
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)
# --- End of fix ---

# --- All imports are now grouped at the top ---
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
    Boolean,
)
from sqlalchemy.engine import Connection
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from neo4j import GraphDatabase, Driver

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
    Column("hashed_password", String, nullable=False),  # Added nullable=False
    Column("is_active", Boolean, default=True),
)


def get_db() -> Connection:
    conn = engine.connect()
    try:
        yield conn
    finally:
        conn.close()


# neo4J

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")


# This class will manage the driver instance
class GraphDatabaseManager:
    def __init__(self):
        self.driver: Driver = None

    def connect(self):
        """Establishes the connection to the Neo4j database."""
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def close(self):
        """Closes the connection."""
        if self.driver is not None:
            self.driver.close()
            self.driver = None


# Create a single instance of the manager for the application's lifecycle
graph_db_manager = GraphDatabaseManager()


# FastAPI dependency to get the database driver
def get_graph_db_driver() -> Driver:
    if graph_db_manager.driver is None:
        graph_db_manager.connect()
    return graph_db_manager.driver


# You might also want to register startup and shutdown events in your api/main.py
# to connect and close the driver cleanly.
