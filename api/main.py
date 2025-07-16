# api/main.py

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from . import database, models
from .routers import users, auth, goals, accomplishments, quests, skills, qa


def create_app():
    app = FastAPI(
        title="SkillForge API",
        description="The core API for the SkillForge engine.",
        version="0.4.0",
    )

    # --- Event Handlers for DB connection ---
    @app.on_event("startup")
    def on_startup():
        # This is the ideal place for initialization logic
        database.create_db_and_tables()

    @app.on_event("shutdown")
    def on_shutdown():
        # Cleanly close database connections
        database.close_db_driver()

    # --- API Routers ---
    # Include all your API endpoints. Let's add prefixes for clarity.
    app.include_router(users.router, prefix="/users", tags=["Users"])
    app.include_router(auth.router, prefix="/token", tags=["Authentication"])
    app.include_router(goals.router, prefix="/goals", tags=["Goals"])
    app.include_router(quests.router, prefix="/quests", tags=["Quests"])
    app.include_router(accomplishments.router, prefix="/accomplishments", tags=["Accomplishments"])
    app.include_router(skills.router, prefix="/skills", tags=["Skills"])
    app.include_router(qa.router, prefix="/qa", tags=["Q&A"])

    # --- Homepage and Static Files ---

    # 1. Define the specific homepage route FIRST.
    @app.get("/", response_class=FileResponse, include_in_schema=False)
    async def read_index():
        return "frontend/index.html"

    # 2. Mount the static directory to handle JS, CSS, etc., AFTER other routes.
    app.mount("/static", StaticFiles(directory="frontend"), name="static")

    return app


# Create the main app instance using the factory
app = create_app()