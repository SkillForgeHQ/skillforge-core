from neo4j import GraphDatabase

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


def add_user_skill(tx, email, skill_name):
    """
    Creates a :HAS_SKILL relationship from a User to a Skill.
    It will create the User and Skill nodes if they don't already exist.
    """
    query = """
    MERGE (u:User {email: $email})
    MERGE (s:Skill {name: $skill_name})
    MERGE (u)-[:HAS_SKILL]->(s)
    """
    tx.run(query, email=email, skill_name=skill_name)


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


def create_user_node(tx, email):
    """
    Creates or finds a :User node in the graph with a unique email.
    """
    query = "MERGE (u:User {email: $email}) RETURN u.email"
    result = tx.run(query, email=email)
    return result.single()["u.email"]


def set_user_skill_mastery(tx, email: str, skill_name: str, mastery_level: int):
    """
    Creates or updates a relationship between a User and a Skill,
    setting the mastery level on the relationship itself.
    """
    query = """
    MATCH (u:User {email: $email})
    MATCH (s:Skill {name: $skill_name})
    // This is the key part: Ensure the skill has a mastery defined at this level
    MATCH (s)-[:HAS_MASTERY]->(m:Mastery {level: $mastery_level})

    // MERGE the relationship and SET or UPDATE its level property
    MERGE (u)-[r:HAS_MASTERY_OF]->(s)
    SET r.level = $mastery_level

    RETURN u.email AS email, r.level AS level, s.name AS skill
    """
    result = tx.run(
        query, email=email, skill_name=skill_name, mastery_level=mastery_level
    )
    return result.single()


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


def add_mastery_level_to_skill(
    tx, skill_name: str, level: int, mastery_name: str, description: str
):
    """
    Creates a :Mastery node and links it to an existing :Skill node.
    """
    query = """
    MATCH (s:Skill {name: $skill_name})
    MERGE (m:Mastery {name: $mastery_name, level: $level, description: $description})
    MERGE (s)-[:HAS_MASTERY]->(m)
    RETURN s.name AS skill, m.name AS mastery_name
    """
    result = tx.run(
        query,
        skill_name=skill_name,
        level=level,
        mastery_name=mastery_name,
        description=description,
    )
    return result.single()
