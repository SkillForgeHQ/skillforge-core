# api/main.py

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from . import database
from skill_system import models
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
        import runpy
        runpy.run_path('init_db.py')

    @app.on_event("shutdown")
    def on_shutdown():
        # Cleanly close database connections
        database.graph_db_manager.close()

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

    # 2. Mount the static directory to handle JS, CSS, etc., AFTER other routes.
    app.mount("/", StaticFiles(directory="frontend"), name="static")

    return app


# Create the main app instance using the factory
app = create_app()