import time
from api.database import engine, metadata

# Give the database a moment to start up
time.sleep(5)

print("Creating database tables...")
metadata.create_all(bind=engine)
print("Tables created successfully.")
