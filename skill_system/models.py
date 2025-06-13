class Skill:
    """Represents a single skill node in the graph."""

    def __init__(self, skill_id: str, name: str, description: str = ""):
        self.skill_id = skill_id
        self.name = name
        self.description = description

        # --- Relationship Attributes ---
        # What skills are needed BEFORE this one?
        self.requires = set()  # Set of skill_ids

        # What skills does this one UNLOCK? (inverse of requires)
        self.unlocks = set()  # Set of skill_ids

        # What broader category does this skill fall into?
        self.is_a_type_of = set()  # Set of parent skill_ids

        # What specific skills are examples of this one?
        self.contains_types = set()  # Set of child skill_ids

    def __repr__(self):
        return f"Skill(id='{self.skill_id}', name='{self.name}"


class SkillGraph:
    """Manages the collection of Skill objects and their relationships."""

    def __init__(self):
        self.skills = {}  # Maps skill_id -> Skill object

    def add_skill(self, skill: Skill):
        """Adds a Skill object to the graph."""
        if skill.skill_id not in self.skills:
            self.skills[skill.skill_id] = skill

    def add_dependency(self, source_skill_id, target_skill_id):
        """This is for the REQUIRES relationship.
        It finds the source_skill and target_skill objects and updates their .unlocks and .requires sets.
        For example: self.skills[target_skill_id].requires.add(source_skill_id)"""
        self.skills[target_skill_id].requires.add(source_skill_id)
        self.skills[source_skill_id].unlocks.add(target_skill_id)

    def add_isa_relationship(self, child_skill_id, parent_skill_id):
        """Similar to above, but for the IS_A_TYPE_OF relationship,
        updating .is_a_type_of and .contains_types"""
        self.skills[child_skill_id].is_a_type_of.add(parent_skill_id)
        self.skills[parent_skill_id].contains_types.add(child_skill_id)

    def get_prerequisites(self, skill_id):
        """Performs a graph traversal (DFS is natural here) backwards from a skill
        along the REQUIRES edges to find all direct and indirect prerequisite skills."""

    def get_skills_unlocked_by(self, skill_id):
        """Performs a forward traversal (BFS or DFS) along the unlocks edges
        to find all skills that a given skill is a prerequisite for."""

    def get_learning_path(self, start_skill_id, target_skill_id):
        """The crown jewel. Implements an algorithm like BFS to find
        the shortest prerequisite path between two skills."""
