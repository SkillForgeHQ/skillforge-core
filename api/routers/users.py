# api/routers/users.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Connection

from .. import crud, schemas
from ..database import get_db
from .auth import get_current_user

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


@router.post("/", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UserCreate, conn: Connection = Depends(get_db)):
    """
    Register a new user.
    """
    db_user = crud.get_user_by_email(conn=conn, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    created_user = crud.create_user(conn=conn, user=user)
    return created_user

@router.get("/me", response_model=schemas.User)
def read_users_me(current_user: schemas.User = Depends(get_current_user)):
    """
    Fetch the currently logged-in user.
    """
    return current_user