# api/routers/auth.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.engine import Connection
from neo4j import GraphDatabase

from .. import crud, schemas, security, graph_crud
from ..database import get_db, get_graph_db_driver

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
    conn: Connection = Depends(get_db),
    neo4j_driver: GraphDatabase.driver = Depends(get_graph_db_driver),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """
    Logs in a user and returns an access token.
    If the user does not exist in Neo4j, it creates them.
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

    # Check and create user in Neo4j if they don't exist
    with neo4j_driver.session() as session:
        # Attempt to find the user in Neo4j.
        # For simplicity, we'll assume a function `get_user_by_email_neo4j` exists or adapt.
        # For now, we'll directly use create_user_node which handles MERGE logic.
        session.execute_write(graph_crud.create_user_node, user.email)

    access_token = security.create_access_token(data={"sub": user.email})

    return {"access_token": access_token, "token_type": "bearer"}
