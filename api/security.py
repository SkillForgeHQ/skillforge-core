# api/security.py

from passlib.context import CryptContext

# Initialize a CryptContext instance.
# We specify that "bcrypt" is the default hashing scheme.
# "deprecated="auto"" will automatically handle upgrading hashes if we change schemes later.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hashes a plaintext password."""
    return pwd_context.hash(password)