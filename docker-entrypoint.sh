#!/bin/sh
set -e

# Run the database initialization script
echo "Running database initialization..."
python init_db.py
echo "Database initialization complete."
# Then, execute the main command passed to the script (e.g., uvicorn)
exec "$@"