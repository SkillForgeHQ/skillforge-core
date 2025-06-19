# api/routers/auth.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.engine import Connection

from .. import crud, schemas, security
from ..database import get_db

router = APIRouter(
    tags=["authentication"],
)

@router.post("/token", response_model=schemas.Token)
def login_for_access_token(
    conn: Connection = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Logs in a user and returns an access token.
    """
    # 1. Get user from DB by email (which is the username here)
    user = crud.get_user_by_email(conn, email=form_data.username)

    # 2. Check if user exists and if the password is correct
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Create the JWT
    access_token = security.create_access_token(
        data={"sub": user.email}
    )

    # 4. Return the token
    return {"access_token": access_token, "token_type": "bearer"}