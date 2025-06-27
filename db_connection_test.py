# db_connection_test.py (Final Version for Today)

import os
import psycopg
import logging
from dotenv import load_dotenv
from neo4j import GraphDatabase

def main():
    """
    Connects to the DB, ensures table exists, inserts a new skill,
    and selects all skills.
    """
    load_dotenv()
    conn_string = (
        f"dbname='{os.getenv('DB_NAME')}' "
        f"user='{os.getenv('DB_USER')}' "
        f"password='{os.getenv('DB_PASSWORD')}' "
        f"host='{os.getenv('DB_HOST')}' "
        f"port='{os.getenv('DB_PORT')}'"
    )

    print("--- Database Interaction Script Started ---")
    try:
        with psycopg.connect(conn_string) as conn:
            with conn.cursor() as cur:
                # 1. Ensure table exists
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

                # 2. Safely INSERT a new skill using parameterization
                skill_to_insert = (
                    "Docker",
                    "Containerization technology for creating isolated application environments.",
                )

                # Use ON CONFLICT DO NOTHING to avoid errors if you run the script multiple times
                insert_query = """
                    INSERT INTO skills (name, description) VALUES (%s, %s)
                    ON CONFLICT (name) DO NOTHING
                    RETURNING id;
                """
                cur.execute(insert_query, skill_to_insert)

                # Fetch the returned ID
                result = cur.fetchone()
                if result:
                    new_skill_id = result[0]
                    print(f"✅ Step 2: Inserted 'Docker' skill with ID: {new_skill_id}")
                else:
                    print("✅ Step 2: 'Docker' skill already exists.")

                # 3. SELECT all skills to verify
                print("\n--- Fetching all skills from database ---")
                cur.execute(
                    "SELECT id, name, description FROM skills ORDER BY created_at;"
                )

                all_skills = cur.fetchall()

                for skill in all_skills:
                    print(f"  - ID: {skill[0]}")
                    print(f"    Name: {skill[1]}")
                    print(f"    Description: {skill[2]}\n")

                print("✅ Step 3: Select operation complete.")

    except psycopg.OperationalError as e:
        print(f"❌ DATABASE CONNECTION FAILED: {e}")
    except Exception as e:
        print(f"❌ AN UNEXPECTED ERROR OCCURRED: {e}")

    load_dotenv()

    # Add this line to get detailed logs from the driver
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    NEO4J_URI = os.getenv("NEO4J_URI")
    NEO4J_USER = os.getenv("NEO4J_USER")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

    print("Attempting to connect to Neo4j...")
    print(f"URI: {NEO4J_URI}")

    try:
        with GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USER, NEO4J_PASSWORD)
        ) as driver:
            driver.verify_connectivity()
            print("Connection successful!")
    except Exception as e:
        print(f"Connection failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
