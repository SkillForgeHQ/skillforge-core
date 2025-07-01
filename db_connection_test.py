# db_connection_test.py

import os
import sys
import psycopg
from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j.debug import watch


def main():
    """
    Connects to the local Postgres DB and then attempts to connect to the
    remote Neo4j Aura DB with detailed debug logging.
    """
    load_dotenv()

    # --- Section 1: PostgreSQL Connection Test ---
    print("--- Database Interaction Script Started ---")
    try:
        conn_string = (
            f"dbname='{os.getenv('DB_NAME')}' "
            f"user='{os.getenv('DB_USER')}' "
            f"password='{os.getenv('DB_PASSWORD')}' "
            f"host='{os.getenv('DB_HOST')}' "
            f"port='{os.getenv('DB_PORT')}'"
        )
        with psycopg.connect(conn_string) as conn:
            with conn.cursor() as cur:
                # Ensure table exists
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS skills (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        name VARCHAR(255) NOT NULL UNIQUE,
                        description TEXT,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    """
                )
                print("✅ Step 1: 'skills' table check complete.")

                # Safely INSERT a new skill
                skill_to_insert = (
                    "Docker",
                    "Containerization technology for creating isolated application environments.",
                )
                insert_query = """
                    INSERT INTO skills (name, description) VALUES (%s, %s)
                    ON CONFLICT (name) DO NOTHING;
                """
                cur.execute(insert_query, skill_to_insert)
                if cur.rowcount > 0:
                    print("✅ Step 2: Inserted 'Docker' skill.")
                else:
                    print("✅ Step 2: 'Docker' skill already exists.")

                # SELECT all skills to verify
                print("\n--- Fetching all skills from database ---")
                cur.execute(
                    "SELECT id, name, description FROM skills ORDER BY created_at;"
                )
                for skill in cur.fetchall():
                    print(f"  - ID: {skill[0]}\n    Name: {skill[1]}\n")

                print("✅ Step 3: Select operation complete.")

    except psycopg.OperationalError as e:
        print(f"❌ POSTGRES CONNECTION FAILED: {e}")
    except Exception as e:
        print(f"❌ AN UNEXPECTED POSTGRES ERROR OCCURRED: {e}")

    # --- Section 2: Neo4j Connection Test with Debug Logging ---
    print("\n--- Attempting to connect to Neo4j ---")
    watch("neo4j", out=sys.stdout)  # You can comment this out to reduce noise

    # Load the .env file
    load_dotenv()

    print("\n--- Reading .env variables ---")
    uri_from_env = os.getenv("NEO4J_URI")
    user_from_env = os.getenv("NEO4J_USERNAME")
    password_from_env = os.getenv("NEO4J_PASSWORD")

    print(f"URI: {uri_from_env}")
    print(f"USER: {user_from_env}")
    print(f"PASSWORD: {password_from_env}")
    print("----------------------------\n")

    try:
        with GraphDatabase.driver(
            uri_from_env,  # Use the variables we just loaded
            auth=(user_from_env, password_from_env),
        ) as driver:
            driver.verify_connectivity()
            print("✅ Connection successful!")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
