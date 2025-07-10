from fastapi import APIRouter, Depends, HTTPException
from typing import List
import uuid

from .. import schemas
from ..database import get_graph_db_session, GraphDBSession


router = APIRouter(
    prefix="/quests",
    tags=["quests"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=schemas.Quest)
def create_quest(
    quest: schemas.QuestCreate, db: GraphDBSession = Depends(get_graph_db_session)
):
    """
    Create a new quest.
    """
    # Assuming QuestCreate schema will be similar to Quest but without id
    # For now, let's assume QuestCreate is:
    # class QuestCreate(BaseModel):
    # name: str
    # description: str
    quest_data = quest.model_dump()
    # Need to import the actual create_quest function from graph_crud
    from ..graph_crud import create_quest as db_create_quest

    db_quest = db.write_transaction(db_create_quest, quest_data)
    if db_quest is None:
        raise HTTPException(status_code=400, detail="Quest could not be created")
    # The db_quest should have an 'id' field after creation
    return schemas.Quest(**db_quest)
