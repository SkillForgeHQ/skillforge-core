# api/main.py

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .routers import users, auth, goals, accomplishments, quests, skills, qa  # All routers imported
from .database import create_db_and_tables, close_db_driver  # For startup/shutdown


def create_app():
    app = FastAPI(
        title="SkillForge API",
        description="The core API for the SkillForge engine.",
        version="0.3.0",  # Let's version up!
    )

    # --- Event Handlers ---
    # Use event handlers for clean startup and shutdown logic
    @app.on_event("startup")
    def on_startup():
        # This is the ideal place for initialization logic
        create_db_and_tables()

    @app.on_event("shutdown")
    def on_shutdown():
        # Cleanly close database connections
        close_db_driver()

    # --- API Routers ---
    # Include all your API endpoints with their prefixes
    app.include_router(users.router, prefix="/users", tags=["Users"])
    app.include_router(auth.router, prefix="/token", tags=["Authentication"])
    app.include_router(goals.router, prefix="/goals", tags=["Goals"])
    app.include_router(quests.router, prefix="/quests", tags=["Quests"])
    app.include_router(accomplishments.router, prefix="/accomplishments", tags=["Accomplishments"])
    app.include_router(skills.router, prefix="/skills", tags=["Skills"])
    app.include_router(qa.router, prefix="/qa", tags=["Q&A"])

    # --- Homepage and Static Files ---
    # Define the specific homepage route FIRST.
    @app.get("/", response_class=FileResponse, include_in_schema=False)
    async def read_index():
        # Ensure the path is correct relative to where the app runs
        return "frontend/index.html"

    # Mount the static directory AFTER all other routes.
    # This will handle requests for /script.js, /styles.css, etc.
    app.mount("/static", StaticFiles(directory="frontend"), name="static")

    return app


# Create the main app instance using the factory
app = create_app()