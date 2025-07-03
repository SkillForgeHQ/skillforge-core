# migrate_skill_relationships.py

import os
from neo4j import GraphDatabase, Driver
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Database Connection ---
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")


def get_graph_db_driver() -> Driver:
    """Returns the Neo4j driver."""
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


# --- Migration Logic ---


def ensure_default_mastery_on_skills(tx):
    """
    Ensures a default Mastery node exists and is connected to every Skill
    that is part of an old user relationship. This makes the next step safe.
    """
    print("  - Running Step 1: Ensuring skills have a default mastery level...")
    query = """
    // Step 1a: Ensure the default Mastery node itself exists.
    MERGE (defaultMastery:Mastery {level: 1, name: 'Beginner', description: 'Default mastery level.'})

    // Step 1b: Find all skills that are part of an old relationship.
    WITH defaultMastery
    MATCH (s:Skill)<-[:HAS_SKILL]-(:User)

    // Step 1c: For each of these skills, ensure it is linked to the default Mastery node.
    // This is idempotent and safe to run multiple times.
    MERGE (s)-[:HAS_MASTERY]->(defaultMastery)

    RETURN count(DISTINCT s) AS skills_updated
    """
    result = tx.run(query)
    count = result.single()["skills_updated"]
    print(f"  - Verified default mastery for {count} skills.")


def migrate_user_relationships(tx):
    """
    Finds old [:HAS_SKILL] relationships, creates new [:HAS_MASTERY_OF]
    relationships with a default level, and deletes the old ones.
    """
    print("  - Running Step 2: Migrating user skill relationships...")
    query = """
    MATCH (u:User)-[old_rel:HAS_SKILL]->(s:Skill)
    // We only process relationships that haven't been fully migrated.
    WHERE NOT EXISTS((u)-[:HAS_MASTERY_OF]->(s))

    // Create the new relationship with the level property.
    MERGE (u)-[new_rel:HAS_MASTERY_OF]->(s)
    SET new_rel.level = 1

    // Delete the old relationship. This is the critical step that failed before.
    DELETE old_rel

    RETURN count(new_rel) AS relationships_migrated
    """
    result = tx.run(query)
    count = result.single()["relationships_migrated"]
    print(f"  - Successfully migrated {count} user relationships.")


# --- Main Execution ---
if __name__ == "__main__":
    driver = get_graph_db_driver()
    print("Connecting to the database to migrate data model...")

    with driver.session() as session:
        # Execute the two migration functions in order within a single session
        session.execute_write(ensure_default_mastery_on_skills)
        session.execute_write(migrate_user_relationships)

    print("Migration complete.")
    driver.close()
