# init_db.py
from api.database import engine, metadata

print("Creating database tables...")
metadata.create_all(bind=engine)
print("Tables created successfully.")
