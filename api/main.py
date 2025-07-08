# api/main.py

import os
from fastapi import FastAPI
from sqlalchemy import create_engine
from .routers import skills, users, auth, goals, qa, accomplishments
import api.database # To access and re-assign api.database.engine

def create_app():
    # Initialize the database engine here, ensuring it uses the
    # environment variables set by pytest_configure for tests.
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL environment variable not set at app creation time.")

    # Re-assign the engine in the database module.
    # This allows existing parts of the app (like get_db) to use the new engine.
    api.database.engine = create_engine(DATABASE_URL)

    # Also, re-initialize Neo4j connection manager if it depends on env vars at init
    # graph_db_manager.connect() could be called here if it wasn't lazy.
    # For langchain_graph, if it's not mock, it also initializes using os.getenv at import.
    # This might need more careful handling if pytest_configure doesn't run early enough for these.
    # However, Neo4j connections are typically lazy or re-established.

    app = FastAPI(
        title="SkillForge API",
        description="The core API for the SkillForge engine.",
        version="0.1.0",
    )

    app.include_router(skills.router, prefix="/skills")
    app.include_router(users.router)
    app.include_router(auth.router)
    app.include_router(goals.router)
    app.include_router(qa.router)
    app.include_router(accomplishments.router)

    @app.get("/", tags=["Root"])
    async def read_root():
        return {"message": "Welcome to the SkillForge API"}

    return app

# If you want to run this with uvicorn directly (e.g. uvicorn api.main:app),
# you might still want a default app instance for that convenience,
# created by the factory.
# For testing, the factory will be called by the test fixture.
# For production, uvicorn can be told to use the factory: uvicorn api.main:create_app --factory
# If a global 'app' is needed for some deployment scripts not using --factory:
# app = create_app()
