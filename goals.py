from datetime import datetime


class Goal:
    _current_unique_id = 0

    def __init__(self, description: str, parent_id: int = None):
        Goal._current_unique_id += 1
        self.id: int = Goal._current_unique_id  # A unique ID for this goal
        self.parent_id = parent_id
        self.description = str(description)  # "Make one cold call"
        self.is_completed: bool = False
        self.completion_date = None
        self.creation_date = datetime.now()

    def mark_complete(self):
        self.is_completed = True
        self.completion_date = datetime.now()


goal_1 = Goal("Learn Python class variables")
goal_2 = Goal("Write a test for unique IDs")

print(
    f"Goal 1: ID={goal_1.id}, Description='{goal_1.description}', Creation Date='{goal_1.creation_date}"
)
print(
    f"Goal 2: ID={goal_2.id}, Description='{goal_2.description}' Creation Date='{goal_2.creation_date}"
)


def test_goal_instantiates_with_a_description():
    g1 = Goal("Learn Python class variables")
    assert g1.description


def test_goal_description_is_always_a_string():
    g1 = Goal(123)
    assert isinstance(g1.description, str)


def test_goal_instantiates_incomplete():
    g1 = Goal("Learn Python class variables")
    assert g1.is_completed is False
    assert isinstance(g1.creation_date, datetime)


def test_goal_object_has_unique_id():
    g1 = Goal("First Goal")
    g2 = Goal("Second Goal")
    assert g1.id != g2.id
    assert g2.id == g1.id + 1


def test_goal_object_has_optional_parent_id():
    g1 = Goal("First Goal")
    g2 = Goal("Second Goal", g1.id)
    assert not g1.parent_id
    assert g2.parent_id == g1.id


def test_can_mark_goal_as_complete():
    g1 = Goal("Finish this test")
    g1.mark_complete()
    assert g1.is_completed is True
    assert isinstance(g1.completion_date, datetime)
