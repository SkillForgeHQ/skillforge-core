import pytest
from datetime import datetime
from uuid import uuid4

from api.schemas import Accomplishment
from neo4j.time import DateTime as Neo4jDateTime  # For mocking

# Simulate a Neo4j timezone object if needed for realistic mocking
# For simplicity, we might not need a full TzInfo object for basic conversion tests.
# from datetime import tzinfo, timedelta
# class MockFixedOffset(tzinfo):
#     def __init__(self, offset_hours):
#         self.__offset = timedelta(hours=offset_hours)
#     def utcoffset(self, dt):
#         return self.__offset
#     def tzname(self, dt):
#         return f"FixedOffset{self.__offset.total_seconds()/3600}"
#     def dst(self, dt):
#         return timedelta(0)


def test_accomplishment_timestamp_conversion():
    """
    Tests that the Accomplishment schema correctly converts a Neo4jDateTime
    object to a Python datetime object for the 'timestamp' field.
    """
    # 1. Arrange: Create a mock Neo4jDateTime object
    # Neo4jDateTime takes year, month, day, hour, minute, second, nanosecond, tzinfo
    # For this test, a simple datetime without explicit timezone should suffice
    # as to_native() handles it. If tz was critical, we'd mock tzinfo.
    mock_neo4j_dt = Neo4jDateTime(
        2023, 10, 26, 12, 30, 15, 500000000
    )  # No tzinfo needed for to_native()

    accomplishment_data_from_neo4j_node = {
        "id": uuid4(),
        "name": "Test Accomplishment",
        "description": "Tested Pydantic conversion.",
        "proof_url": None,
        "timestamp": mock_neo4j_dt,  # This is what comes from the Neo4j Node attribute
    }

    # 2. Act: Validate the data using the Pydantic model
    validated_accomplishment = Accomplishment.model_validate(
        accomplishment_data_from_neo4j_node
    )

    # 3. Assert: Check that the timestamp is now a Python datetime object
    assert isinstance(validated_accomplishment.timestamp, datetime)
    assert validated_accomplishment.timestamp.year == 2023
    assert validated_accomplishment.timestamp.month == 10
    assert validated_accomplishment.timestamp.day == 26
    assert validated_accomplishment.timestamp.hour == 12
    assert validated_accomplishment.timestamp.minute == 30
    assert validated_accomplishment.timestamp.second == 15
    assert (
        validated_accomplishment.timestamp.microsecond == 500000
    )  # Nanoseconds to microseconds

    # Test with a Python datetime object directly (should pass through)
    python_dt = datetime.now()
    accomplishment_data_with_python_dt = {
        "id": uuid4(),
        "name": "Test Accomplishment 2",
        "description": "Tested with Python datetime.",
        "timestamp": python_dt,
    }
    validated_accomplishment_2 = Accomplishment.model_validate(
        accomplishment_data_with_python_dt
    )
    assert validated_accomplishment_2.timestamp == python_dt

    # Test with a string (should fail or be handled by other Pydantic parsing if allowed)
    # In this case, our validator is 'before' Pydantic's string parsing for datetime.
    # Pydantic itself can parse ISO format strings to datetime.
    iso_dt_string = "2023-11-01T10:00:00Z"
    accomplishment_data_with_iso_string = {
        "id": uuid4(),
        "name": "Test Accomplishment 3",
        "description": "Tested with ISO string.",
        "timestamp": iso_dt_string,
    }
    validated_accomplishment_3 = Accomplishment.model_validate(
        accomplishment_data_with_iso_string
    )
    assert isinstance(validated_accomplishment_3.timestamp, datetime)
    assert validated_accomplishment_3.timestamp.year == 2023
    assert validated_accomplishment_3.timestamp.month == 11
    assert validated_accomplishment_3.timestamp.day == 1
    assert validated_accomplishment_3.timestamp.hour == 10

    print("Successfully tested Accomplishment timestamp conversion.")


if __name__ == "__main__":
    # This allows running the test directly for quick checks, though pytest is preferred.
    test_accomplishment_timestamp_conversion()
