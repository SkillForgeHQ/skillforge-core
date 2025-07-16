# api/main.py

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .routers import users, auth, goals, accomplishments, quests, skills, qa
from .database import create_db_and_tables, close_db_driver


def create_app():
    app = FastAPI(
        title="SkillForge API",
        description="The core API for the SkillForge engine.",
        version="0.4.0",  # Let's version up!
    )

    # --- Event Handlers for DB connection ---
    @app.on_event("startup")
    def on_startup():
        create_db_and_tables()

    @app.on_event("shutdown")
    def on_shutdown():
        close_db_driver()

    # --- API Routers ---
    # Mount all your API endpoints under a common prefix, like /api
    # This is a best practice to avoid conflicts with the frontend.
    app.include_router(users.router, prefix="/api/users", tags=["Users"])
    app.include_router(auth.router, prefix="/api/token", tags=["Authentication"])
    app.include_router(goals.router, prefix="/api/goals", tags=["Goals"])
    app.include_router(quests.router, prefix="/api/quests", tags=["Quests"])
    app.include_router(accomplishments.router, prefix="/api/accomplishments", tags=["Accomplishments"])
    app.include_router(skills.router, prefix="/api/skills", tags=["Skills"])
    app.include_router(qa.router, prefix="/api/qa", tags=["Q&A"])

    # --- Homepage and Static Files ---
    # This must come AFTER all API routes
    app.mount("/", StaticFiles(directory="frontend", html=True), name="static")

    # Define a catch-all endpoint to always serve the index.html for any non-API, non-file path
    # This is crucial for single-page applications with client-side routing
    @app.get("/{full_path:path}", response_class=FileResponse, include_in_schema=False)
    async def catch_all(full_path: str):
        return FileResponse("frontend/index.html")

    return app


# Create the main app instance
app = create_app()