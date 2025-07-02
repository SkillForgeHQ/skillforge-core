# api/main.py

from fastapi import FastAPI
from .routers import skills, users, auth

app = FastAPI(
    title="SkillForge API",
    description="The core API for the SkillForge engine.",
    version="0.1.0",
)

app.include_router(skills.router, prefix="/skills")
app.include_router(users.router)
app.include_router(auth.router)


@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the SkillForge API"}
