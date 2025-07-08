from neo4j import GraphDatabase
from typing import List

# Create Operations


def create_skill(tx, skill_name):
    """
    Creates a new skill node in the database.
    This function is designed to be called within a transaction
    """
    query = "MERGE (s:Skill {name: $skill_name}) " "RETURN s.name AS name"
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


def update_skill(tx, old_name, new_name):
    """
    Updates the name of an existing skill node.
    """
    query = (
        "MATCH (s:Skill {name: $old_name}) "
        "SET s.name = $new_name "
        "RETURN s.name AS name"
    )
    result = tx.run(query, old_name=old_name, new_name=new_name)
    return result.single()


# --- Delete Operations ---


def delete_skill(tx, skill_name):
    """
    Deletes a skill node and its relationships.
    """
    # Using DETACH DELETE ensures that the node and any relationships
    # attached to it are deleted, preventing orphaned relationships.
    query = "MATCH (s:Skill {name: $skill_name}) DETACH DELETE s"
    tx.run(query, skill_name=skill_name)


def add_skill_dependency(tx, parent_skill_name, child_skill_name):
    """
    Creates a DEPENDS_ON relationship from a parent skill to a child skill.
    """
    query = (
        "MATCH (parent:Skill {name: $parent_skill_name}) "
        "MATCH (child:Skill {name: $child_skill_name}) "
        "MERGE (parent)-[:DEPENDS_ON]->(child)"
    )
    tx.run(
        query, parent_skill_name=parent_skill_name, child_skill_name=child_skill_name
    )


# In api/graph_crud.py


def get_skill_dependencies(tx, skill_name):
    """
    Finds all skills that the given skill has a DEPENDS_ON relationship to.
    """
    query = (
        "MATCH (s:Skill {name: $skill_name})-[:DEPENDS_ON]->(dependency:Skill) "
        "RETURN dependency.name AS dependency_name"
    )
    result = tx.run(query, skill_name=skill_name)
    return [record["dependency_name"] for record in result]


# In api/graph_crud.py


def get_consolidated_learning_path(tx, skill_name):
    """
    Finds all prerequisite skills for a target skill and returns them
    as a single, unique, ordered learning path.
    """
    # This query finds all prerequisite nodes, calculates their "depth"
    # (longest path to a root), and returns a unique, sorted list of skill names.
    query = """
    MATCH (target:Skill {name: $skill_name})
    // Find all skills that the target depends on (at any depth)
    MATCH (prereq) WHERE (target)-[:DEPENDS_ON*0..]->(prereq)
    // For each of those skills, find its longest path back to a true root
    MATCH p = (prereq)-[:DEPENDS_ON*0..]->(root)
    WHERE NOT (root)-[:DEPENDS_ON]->()
    // Return the unique skills, ordered by their depth (most fundamental first)
    WITH prereq, MAX(length(p)) AS depth
    ORDER BY depth DESC
    WITH COLLECT(prereq.name) AS path_with_duplicates
    // Unwind the collection and get distinct elements to preserve order
    UNWIND path_with_duplicates as skill_name
    RETURN COLLECT(DISTINCT skill_name) as path
    """
    result = tx.run(query, skill_name=skill_name)
    # The query now returns a single record containing one path
    record = result.single()
    return record["path"] if record else []


def create_user_node(tx, email):
    """
    Creates a :User node in the graph with a unique email.
    """
    query = "MERGE (u:User {email: $email}) RETURN u.email"
    result = tx.run(query, email=email)
    return result.single()["u.email"]


# ---- Accomplishment CRUD Operations ----
def create_accomplishment(tx, user_email: str, accomplishment_data: dict):
    """
    Creates an Accomplishment node and links it to a user.
    """
    query = """
    MATCH (u:User {email: $user_email})
    CREATE (a:Accomplishment)
    SET a = $accomplishment_data, a.id = randomUUID(), a.timestamp = datetime()
    CREATE (u)-[:COMPLETED]->(a)
    RETURN a
    """
    result = tx.run(
        query, user_email=user_email, accomplishment_data=accomplishment_data
    )
    return result.single()["a"]


def link_accomplishment_to_skill(tx, accomplishment_id: str, skill_name: str):
    """
    Links an Accomplishment to a Skill with a DEMONSTRATES relationship.
    """
    query = """
    MATCH (a:Accomplishment {id: $accomplishment_id})
    MATCH (s:Skill {name: $skill_name})
    MERGE (a)-[:DEMONSTRATES]->(s)
    """
    tx.run(query, accomplishment_id=accomplishment_id, skill_name=skill_name)


def get_user_skills(tx, email):
    """
    Retrieves a list of all skills a user has.
    """
    query = """
    MATCH (u:User {email: $email})-[:HAS_SKILL]->(s:Skill)
    RETURN s.name AS skill_name
    """
    result = tx.run(query, email=email)
    return [record["skill_name"] for record in result]


def remove_user_skill(tx, email, skill_name):
    """
    Deletes the :HAS_SKILL relationship between a User and a Skill.
    """
    query = """
    MATCH (u:User {email: $email})-[r:HAS_SKILL]->(s:Skill {name: $skill_name})
    DELETE r
    """
    tx.run(query, email=email, skill_name=skill_name)


def get_user_skills_by_accomplishments(tx, email: str) -> List[str]:
    """
    Retrieves a list of unique skill names a user has demonstrated through accomplishments.
    """
    query = """
    MATCH (u:User {email: $email})-[:COMPLETED]->(a:Accomplishment)-[:DEMONSTRATES]->(s:Skill)
    RETURN COLLECT(DISTINCT s.name) AS skills
    """
    result = tx.run(query, email=email)
    record = result.single()
    return record["skills"] if record and record["skills"] is not None else []


def get_accomplishment_details(tx, accomplishment_id):
    query = """
    MATCH (u:User)-[:COMPLETED]->(a:Accomplishment {id: $accomplishment_id})
    RETURN u, a
    """
    result = tx.run(query, accomplishment_id=str(accomplishment_id))
    record = result.single()
    if record:
        return {"user": record["u"], "accomplishment": record["a"]}
    return None
