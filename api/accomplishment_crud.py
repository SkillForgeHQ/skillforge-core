from neo4j import GraphDatabase, Driver
from . import graph_crud

# A mapping from the AI's string output to the integer levels in our database
MASTERY_LEVEL_MAP = {
    "Beginner": 1,
    "Intermediate": 2,
    "Advanced": 3,
    "Expert": 4,
}

# Default mastery levels to create for any new skill
DEFAULT_MASTERY_DEFINITIONS = {
    1: {
        "name": "Beginner",
        "description": "Has a basic understanding of the concepts.",
    },
    2: {
        "name": "Intermediate",
        "description": "Can apply the skill to simple projects without supervision.",
    },
    3: {
        "name": "Advanced",
        "description": "Can apply the skill to complex projects and mentor others.",
    },
    4: {
        "name": "Expert",
        "description": "Is a recognized authority on the skill, pushing its boundaries.",
    },
}


def get_all_skill_names(driver: Driver) -> list[str]:
    """
    Retrieves a list of all skill names from the graph.
    This is a convenience wrapper around the graph_crud function.
    """
    with driver.session() as session:
        skills = session.read_transaction(graph_crud.get_all_skills)
        return skills


def add_new_skill_with_masteries(driver: Driver, skill_name: str):
    """
    Creates a new skill and immediately populates it with the four
    standard mastery level nodes. This is a high-level, transactional function.
    """
    with driver.session() as session:
        session.write_transaction(graph_crud.create_skill, skill_name)
        for level, details in DEFAULT_MASTERY_DEFINITIONS.items():
            session.write_transaction(
                graph_crud.add_mastery_level_to_skill,
                skill_name,
                level,
                details["name"],
                details["description"],
            )
    print(f"Successfully created skill '{skill_name}' with all mastery levels.")


def assign_mastery_to_user(
    driver: Driver, email: str, skill_name: str, mastery_level_str: str
):
    """
    Assigns a mastery level to a user for a specific skill.
    It translates the AI's string-based level to the integer required by the database.
    """
    # Translate the string level (e.g., "Intermediate") to an integer (e.g., 2)
    mastery_level_int = MASTERY_LEVEL_MAP.get(mastery_level_str)

    if mastery_level_int is None:
        print(
            f"Warning: Invalid mastery level '{mastery_level_str}' for skill '{skill_name}'. Skipping."
        )
        return

    with driver.session() as session:
        session.write_transaction(
            graph_crud.set_user_skill_mastery,
            email,
            skill_name,
            mastery_level_int,
        )
    print(
        f"Successfully assigned {skill_name} at level {mastery_level_str} to {email}."
    )
