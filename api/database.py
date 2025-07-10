# api/database.py

import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.graphs import Neo4jGraph  # Reverted import

env_path = Path(__file__).parent.parent / ".env"
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

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
metadata = MetaData()

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
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")  # Corrected variable name
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

if not NEO4J_URI:
    raise ValueError("Missing NEO4J_URI environment variable. Cannot connect to Neo4j.")
if not NEO4J_USERNAME:
    raise ValueError(
        "Missing NEO4J_USERNAME environment variable. Cannot connect to Neo4j."
    )
if not NEO4J_PASSWORD:
    raise ValueError(
        "Missing NEO4J_PASSWORD environment variable. Cannot connect to Neo4j."
    )


# This class will manage the driver instance
class GraphDatabaseManager:
    def __init__(self):
        self.driver: Driver = None

    def connect(self):
        """Establishes the connection to the Neo4j database."""
        self.driver = GraphDatabase.driver(
            NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
        )

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

# Define GraphDBSession type for clarity, can be aliased to neo4j.Session
from neo4j import Session as Neo4jSession

GraphDBSession = Neo4jSession

# FastAPI dependency to get a Neo4j session
def get_graph_db_session() -> GraphDBSession:
    driver = get_graph_db_driver()
    with driver.session() as session:
        yield session


# This object will be used by our RAG chain.
if os.getenv("TESTING_MODE") == "True":
    from unittest.mock import MagicMock

    langchain_graph = MagicMock()
    # You might want to configure the mock further if its attributes are accessed
    # e.g., langchain_graph.schema = MagicMock()
else:
    import warnings

    # Removed problematic import: from langchain.chains.graph_qa.deprecated_schema import LangChainDeprecationWarning

    with warnings.catch_warnings():
        # Filter the specific LangChainDeprecationWarning related to Neo4jGraph from langchain_community
        # If the exact warning class is hard to import or pin down, use a more general category
        # or filter by message if necessary. For now, trying to catch a general one if specific isn't available.
        # The warning was: "The class `Neo4jGraph` was deprecated in LangChain 0.3.8 and will be removed in 1.0."
        # This warning originates from langchain_community.graphs.Neo4jGraph
        warnings.filterwarnings(
            "ignore",
            category=DeprecationWarning,  # Using general DeprecationWarning, refine if possible
            message="The class `Neo4jGraph` was deprecated in LangChain 0.3.8*",  # Match start of message
        )
        langchain_graph = Neo4jGraph(
            url=NEO4J_URI, username=NEO4J_USERNAME, password=NEO4J_PASSWORD
        )
