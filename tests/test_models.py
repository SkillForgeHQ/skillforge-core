# tests/test_models.py

import pytest
from skill_system.models import Skill, SkillGraph



def test_add_skill_to_graph():
    """Tests that a Skill object is correctly added to the SkillGraph's skills dictionary."""
    # 1. Arrange: Set up the objects we need for the test.
    graph = SkillGraph()
    skill_to_add = Skill('py_basics', 'Python Basics', 'Learn basic syntax and types.')

    #2. Act:  Call the method you are testing
    graph.add_skill(skill_to_add)

    #3. Assert:  Check that the outcome is what you expect.
    #  Check that the key exists in the dictionary
    assert 'py_basics' in graph.skills
    # Check that the object associated with the key is the one we added
    assert graph.skills['py_basics'] == skill_to_add
    # Check that the graph now contains exactly one skill
    assert len(graph.skills) == 1