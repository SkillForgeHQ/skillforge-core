import sys  # <--- ADD THIS AT THE TOP

from fastapi import FastAPI
from .routers import skills

app = FastAPI(title="SkillForge API")

app.include_router(
    skills.router,
    prefix="/skills",
    tags=["Skills"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to the SkillForge API"}

@app.get("/debug-modules")  # <--- ADD THIS ENTIRE BLOCK
def get_loaded_modules():
    return sorted(list(sys.modules.keys()))