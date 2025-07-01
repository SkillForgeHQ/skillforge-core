from neo4j import GraphDatabase

# Create Operations

def create_skill(tx, skill_name):
    """
    Creates a new skill node in the database.
    This function is designed to be called within a transaction
    """
    query = (
        "MERGE (s:Skill {name: $skill_name}) "
        "RETURN s.name AS name"
    )
    result = tx.run(query, skill_name=skill_name)
    return result.single()

# Read Operations

def get_all_skills(tx):
    """
    Retrieves all skill nodes from the database.
    This function is designed to be called within a transaction
    """
    query = "MATCH (s:Skill) RETURN s.name AS name ORDER BY s.name"
    result = tx.run(query)
    return [record["name"] for record in result]

def get_skill_by_name(tx, skill_name):
    """
    Finds a specific skill by its name.
    """
    query = "MATCH (s:Skill {name: $skill_name}) RETURN s.name AS name"
    result = tx.run(query, skill_name=skill_name)
    return result.single()
