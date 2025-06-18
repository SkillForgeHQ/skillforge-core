# tests/test_models.py

import pytest
from skill_system.models import Skill, SkillGraph


def test_add_skill_to_graph():
    """Tests that a Skill object is correctly added to the SkillGraph's skills dictionary."""
    # 1. Arrange: Set up the objects we need for the test.
    graph = SkillGraph()
    skill_to_add = Skill("py_basics", "Python Basics", "Learn basic syntax and types.")

    # 2. Act:  Call the method you are testing
    graph.add_skill(skill_to_add)

    # 3. Assert:  Check that the outcome is what you expect.
    #  Check that the key exists in the dictionary
    assert "py_basics" in graph.skills
    # Check that the object associated with the key is the one we added
    assert graph.skills["py_basics"] == skill_to_add
    # Check that the graph now contains exactly one skill
    assert len(graph.skills) == 1


def test_add_dependency():
    graph = SkillGraph()
    prerequisite_skill = Skill(
        "py_basics", "Python Basics", "Learn basic syntax and types."
    )
    target_skill = Skill(
        "py_intermediate", "Python Intermediate", "Learn data structures, loops."
    )

    graph.add_skill(prerequisite_skill)
    graph.add_skill(target_skill)
    graph.add_dependency("py_basics", "py_intermediate")

    assert "py_basics" in graph.skills["py_intermediate"].requires
    assert "py_intermediate" in graph.skills["py_basics"].unlocks


def test_isa_relationship():
    graph = SkillGraph()
    child_skill = Skill("id_spoon", "Identify Spoon", "Can recognize a spoon")
    parent_skill = Skill(
        "id_objects", "Identify Objects", "Object Identification Category"
    )

    graph.add_skill(child_skill)
    graph.add_skill(parent_skill)
    graph.add_isa_relationship(child_skill.skill_id, parent_skill.skill_id)

    assert "id_spoon" in graph.skills["id_objects"].contains_types
    assert "id_objects" in graph.skills["id_spoon"].is_a_type_of
