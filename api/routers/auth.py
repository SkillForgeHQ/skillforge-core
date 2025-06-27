# api/routers/auth.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.engine import Connection

from .. import crud, schemas, security
from ..database import get_db

# This scheme will look for a token in the "Authorization" header.
# The `tokenUrl` points to our login endpoint.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

router = APIRouter(
    tags=["authentication"],
)


async def get_current_user(
    conn: Connection = Depends(get_db), token: str = Depends(oauth2_scheme)
):
    """
    Dependency to get the current user from a token.
    Decodes the token, validates the signature, and fetches the user from the DB.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, security.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = crud.get_user_by_email(conn, email=email)
    if user is None:
        raise credentials_exception
    return user


@router.post("/token", response_model=schemas.Token)
def login_for_access_token(
    conn: Connection = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Logs in a user and returns an access token.
    """
    user = crud.get_user_by_email(conn, email=form_data.username)

    if not user or not security.verify_password(
        form_data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = security.create_access_token(data={"sub": user.email})

    return {"access_token": access_token, "token_type": "bearer"}
