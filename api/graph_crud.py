import uuid
from neo4j import GraphDatabase
from typing import List
from . import schemas # Import schemas

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


# ---- Quest CRUD Operations ----
def create_quest(tx, quest_data):
    """Creates a new Quest node and returns it."""
    new_id = str(uuid.uuid4())
    query = """
    CREATE (q:Quest {id: $id, name: $name, description: $description})
    RETURN q
    """
    result = tx.run(query, id=new_id, **quest_data).single()
    return result['q']


def create_quest_and_link_to_user(tx, quest_data, user_email):
    """
    Creates a new Quest node, links it to the specified User with a HAS_QUEST relationship,
    and returns the Quest node.
    """
    new_quest_id = str(uuid.uuid4())
    # Create the Quest node
    create_quest_query = """
    CREATE (q:Quest {id: $id, name: $name, description: $description})
    RETURN q
    """
    quest_node = tx.run(create_quest_query, id=new_quest_id, name=quest_data['name'], description=quest_data['description']).single()['q']

    # Link the Quest to the User
    link_user_to_quest_query = """
    MATCH (u:User {email: $user_email})
    MATCH (q:Quest {id: $quest_id})
    MERGE (u)-[:HAS_QUEST]->(q)
    """
    tx.run(link_user_to_quest_query, user_email=user_email, quest_id=new_quest_id)

    return quest_node


def create_goal_and_link_to_user(tx, goal_data: schemas.GoalCreate, user_email: str):
    """
    Creates a new Goal node, links it to the user, and returns the Goal node.
    """
    goal_id = str(uuid.uuid4())
    query = """
    MATCH (u:User {email: $user_email})
    CREATE (g:Goal {
        id: $id,
        user_email: $user_email,
        goal_text: $goal_text,
        status: 'in-progress',
        full_plan_json: $full_plan_json
    })
    CREATE (u)-[:HAS_GOAL]->(g)
    RETURN g
    """
    result = tx.run(
        query,
        id=goal_id,
        user_email=user_email,
        goal_text=goal_data.goal_text,
        full_plan_json=goal_data.full_plan_json
    ).single()
    return result['g']


def advance_goal(tx, completed_quest_id: str, user_email: str):
    """Advance a goal's state machine after a quest is completed."""
    import json

    # Locate the goal that currently has this quest as its active quest. We only
    # need the Goal node here; the Quest's title will be fetched separately.
    find_query = """
    MATCH (u:User {email: $user_email})-[:HAS_GOAL]->(g:Goal)-[:HAS_ACTIVE_QUEST]->(q:Quest {id: $quest_id})
    RETURN g
    """
    record = tx.run(find_query, user_email=user_email, quest_id=completed_quest_id).single()
    if not record:
        return None

    goal_node = record["g"]

    plan = json.loads(goal_node["full_plan_json"])

    # Look up the completed quest's name to determine its position in the plan
    get_name_query = "MATCH (q:Quest {id: $quest_id}) RETURN q.name AS name"
    quest_name_record = tx.run(get_name_query, quest_id=completed_quest_id).single()
    completed_name = quest_name_record["name"] if quest_name_record else None
    completed_index = next((i for i, t in enumerate(plan) if t["title"] == completed_name), -1)
    if completed_index == -1:
        return None

    # Remove the active quest relationship
    delete_rel_query = """
    MATCH (g:Goal {id: $goal_id})-[r:HAS_ACTIVE_QUEST]->(q:Quest {id: $quest_id})
    DELETE r
    """
    tx.run(delete_rel_query, goal_id=goal_node["id"], quest_id=completed_quest_id)

    # If there is a next task, create the quest and set it as active
    if completed_index + 1 < len(plan):
        next_task = plan[completed_index + 1]
        new_quest_data = {"name": next_task["title"], "description": next_task["description"]}
        new_quest_node = create_quest_and_link_to_user(tx, new_quest_data, user_email)

        # Link goal to new quest as active
        link_active_query = """
        MATCH (g:Goal {id: $goal_id})
        MATCH (q:Quest {id: $quest_id})
        CREATE (g)-[:HAS_ACTIVE_QUEST]->(q)
        """
        tx.run(link_active_query, goal_id=goal_node["id"], quest_id=new_quest_node["id"])

        # Link old quest to new quest for history
        precedes_query = """
        MATCH (old:Quest {id: $old_id})
        MATCH (new:Quest {id: $new_id})
        CREATE (old)-[:PRECEDES]->(new)
        """
        tx.run(precedes_query, old_id=completed_quest_id, new_id=new_quest_node["id"])

        return new_quest_node

    # Otherwise mark the goal completed and link achievement
    complete_query = """
    MATCH (g:Goal {id: $goal_id})
    SET g.status = 'completed'
    """
    tx.run(complete_query, goal_id=goal_node["id"])

    achieve_query = """
    MATCH (u:User {email: $user_email})
    MATCH (g:Goal {id: $goal_id})
    MERGE (u)-[:ACHIEVED_GOAL]->(g)
    """
    tx.run(achieve_query, user_email=user_email, goal_id=goal_node["id"])

    return None


# ---- Accomplishment CRUD Operations ----
def create_accomplishment(tx, user: schemas.User, accomplishment_data, quest_id: str = None):
    """
    Creates an Accomplishment, links it to the user, and optionally
    links it to the Quest it fulfills.
    """
    accomplishment_id_str = str(uuid.uuid4())

    # Prepare data for Cypher query, excluding 'user_email' and 'quest_id' if they exist
    # as they are handled separately or not part of the node properties.
    # Add 'id' to the properties.
    props_to_set = {
        "id": accomplishment_id_str,
        "name": accomplishment_data.get("name"),
        "description": accomplishment_data.get("description"),
        "proof_url": accomplishment_data.get("proof_url"), # Will be None if not provided
    }

    query = """
    MATCH (u:User {email: $user_email})
    CREATE (a:Accomplishment)
    SET a = $props, a.timestamp = datetime()
    CREATE (u)-[:COMPLETED]->(a)
    RETURN a
    """
    # Use user.email from the user object
    result = tx.run(query, user_email=user.email, props=props_to_set).single()
    accomplishment_node = result['a']

    # Determine the quest_id to use: either from the direct parameter or from accomplishment_data
    final_quest_id = quest_id if quest_id is not None else accomplishment_data.get("quest_id")

    if final_quest_id:
        link_query = """
        MATCH (a:Accomplishment {id: $accomplishment_id})
        MATCH (q:Quest {id: $quest_id})
        CREATE (a)-[:FULFILLS]->(q)
        """
        tx.run(link_query, accomplishment_id=accomplishment_id_str, quest_id=str(final_quest_id))

    return accomplishment_node


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


def store_vc_receipt(tx, accomplishment_id, vc_receipt):
    """
    Finds the [:COMPLETED] relationship for an accomplishment and adds
    properties to it to store a receipt of the issued Verifiable Credential.
    """
    query = """
    MATCH (u:User)-[r:COMPLETED]->(a:Accomplishment {id: $accomplishment_id})
    SET r.vc_id = $vc_id,
        r.vc_issuanceDate = $vc_issuanceDate
    RETURN r
    """
    tx.run(
        query,
        accomplishment_id=str(accomplishment_id),
        vc_id=vc_receipt["id"],
        vc_issuanceDate=vc_receipt["issuanceDate"]
    )


def user_exists(tx, email: str) -> bool:
    """
    Checks if a user with the given email exists in the database.
    Returns True if the user exists, False otherwise.
    """
    query = """
    MATCH (u:User {email: $email})
    RETURN count(u) > 0 AS user_exists
    """
    result = tx.run(query, email=email).single()
    return result["user_exists"] if result else False
