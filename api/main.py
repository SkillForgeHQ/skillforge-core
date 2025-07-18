# api/main.py

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import create_engine
from .routers import skills, users, auth, goals, qa, accomplishments, quests # Added quests
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

    # Include routers with their default prefixes (used by tests)
    app.include_router(skills.router, prefix="/skills")
    app.include_router(users.router)
    app.include_router(auth.router)
    app.include_router(goals.router)
    app.include_router(qa.router)
    app.include_router(accomplishments.router)
    app.include_router(quests.router)  # Added quests router

    # Also expose the same routes under /api for the frontend
    api_prefix = "/api"
    app.include_router(skills.router, prefix=f"{api_prefix}/skills")
    app.include_router(users.router, prefix=api_prefix)
    app.include_router(auth.router, prefix=api_prefix)
    app.include_router(goals.router, prefix=api_prefix)
    app.include_router(qa.router, prefix=api_prefix)
    app.include_router(accomplishments.router, prefix=api_prefix)
    app.include_router(quests.router, prefix=api_prefix)

    # Mount the frontend directory to serve static files
    app.mount("/static", StaticFiles(directory="frontend"), name="static")

    @app.get("/", include_in_schema=False)
    async def read_root():
        return FileResponse("frontend/index.html")

    return app

# If you want to run this with uvicorn directly (e.g. uvicorn api.main:app),
# you might still want a default app instance for that convenience,
# created by the factory.
# For testing, the factory will be called by the test fixture.
# For production, uvicorn can be told to use the factory: uvicorn api.main:create_app --factory
# If a global 'app' is needed for some deployment scripts not using --factory:
app = create_app()
