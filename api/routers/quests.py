from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
import uuid

from .. import schemas
from ..database import get_graph_db_session, GraphDBSession
from .auth import get_current_user


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
    quest_data = quest.model_dump()
    from ..graph_crud import create_quest as db_create_quest

    db_quest = db.write_transaction(db_create_quest, quest_data)
    if db_quest is None:
        raise HTTPException(status_code=400, detail="Quest could not be created")
    return schemas.Quest(**db_quest)


@router.post("/{quest_id}/complete", response_model=Optional[schemas.Quest])
def complete_quest(
    quest_id: uuid.UUID,
    db: GraphDBSession = Depends(get_graph_db_session),
    current_user: schemas.User = Depends(get_current_user),
):
    """
    Marks a quest as complete and advances the goal to the next quest.
    Returns the next quest, or null if the goal is complete.
    """
    from ..graph_crud import advance_goal

    next_quest_node = db.write_transaction(
        advance_goal, str(quest_id), current_user.email
    )

    if next_quest_node:
        return schemas.Quest.from_orm(next_quest_node)
    return None
