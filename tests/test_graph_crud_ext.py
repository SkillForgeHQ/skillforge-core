import pytest
import uuid
from api import graph_crud
from api.schemas import AccomplishmentCreate, Quest

# Mock Neo4j transaction object
class MockTransaction:
    def __init__(self):
        self.queries = []
        self.parameters = []
        self.return_value = None

    def run(self, query, **kwargs):
        self.queries.append(query)
        self.parameters.append(kwargs)
        # Simulate returning a single record or None
        if self.return_value is not None:
            if isinstance(self.return_value, list) and not self.return_value: # Empty list for no records
                return MockResult([])
            if isinstance(self.return_value, list): # List of records
                 return MockResult([MockRecord(item) for item in self.return_value])
            return MockSingleResult(MockRecord(self.return_value)) # Single record
        return MockResult([]) # Default to no records

    def single(self):
        # This is part of the Neo4j driver's result object, not transaction directly
        # Handled by MockResult and MockSingleResult
        pass

class MockResult:
    def __init__(self, records):
        self._records = records
        self._position = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._position < len(self._records):
            record = self._records[self._position]
            self._position += 1
            return record
        else:
            raise StopIteration

    def single(self):
        if len(self._records) == 1:
            return self._records[0]
        elif not self._records:
            return None
        else:
            # This mimics Neo4j driver behavior more closely
            raise Exception("More than one record found")


class MockSingleResult:
    def __init__(self, record):
        self._record = record

    def single(self):
        return self._record

class MockRecord:
    def __init__(self, data):
        self._data = data

    def __getitem__(self, key):
        return self._data[key]

    def get(self, key, default=None):
        return self._data.get(key, default)

# --- Quest Tests ---
def test_create_quest():
    tx = MockTransaction()
    quest_data = {"name": "Test Quest", "description": "A quest for testing."}

    # Simulate the expected return structure from Neo4j for a Quest node
    mock_quest_node_data = {
        "id": str(uuid.uuid4()), # The function generates its own ID
        "name": quest_data["name"],
        "description": quest_data["description"]
    }
    tx.return_value = {"q": mock_quest_node_data} # tx.run().single() will return this record

    result_node = graph_crud.create_quest(tx, quest_data)

    assert len(tx.queries) == 1
    assert "CREATE (q:Quest {id: $id, name: $name, description: $description})" in tx.queries[0]
    assert tx.parameters[0]['name'] == quest_data["name"]
    assert tx.parameters[0]['description'] == quest_data["description"]
    assert 'id' in tx.parameters[0] # Check that an ID is passed

    assert result_node is not None
    assert result_node["name"] == quest_data["name"]
    assert result_node["description"] == quest_data["description"]
    assert "id" in result_node # The returned node should have the ID

# --- Accomplishment Tests ---
def test_create_accomplishment_without_quest_id():
    tx = MockTransaction()
    user_email = "test@example.com"
    accomplishment_data = AccomplishmentCreate(
        name="Test Accomplishment",
        description="Description of test accomplishment.",
        proof_url="http://example.com/proof"
    )

    mock_accomplishment_node_data = {
        "id": str(uuid.uuid4()),
        "name": accomplishment_data.name,
        "description": accomplishment_data.description,
        "proof_url": accomplishment_data.proof_url,
        # timestamp will be added by the query
    }
    tx.return_value = {"a": mock_accomplishment_node_data}

    result_node = graph_crud.create_accomplishment(tx, user_email, accomplishment_data)

    assert len(tx.queries) == 1
    assert "MATCH (u:User {email: $user_email})" in tx.queries[0]
    assert "CREATE (a:Accomplishment {" in tx.queries[0]
    assert "CREATE (u)-[:COMPLETED]->(a)" in tx.queries[0]

    params = tx.parameters[0]
    assert params['user_email'] == user_email
    assert params['name'] == accomplishment_data.name
    assert params['description'] == accomplishment_data.description
    assert params['proof_url'] == accomplishment_data.proof_url
    assert 'id' in params # Check that an ID is passed for the accomplishment

    assert result_node is not None
    assert result_node["name"] == accomplishment_data.name

def test_create_accomplishment_with_quest_id():
    tx = MockTransaction()
    user_email = "test@example.com"
    quest_id = uuid.uuid4()
    accomplishment_data = AccomplishmentCreate(
        name="Test Accomplishment for Quest",
        description="Description of test accomplishment fulfilling a quest.",
        quest_id=quest_id
    )

    mock_accomplishment_node_data = {
        "id": str(uuid.uuid4()), # The function generates its own ID
        "name": accomplishment_data.name,
        "description": accomplishment_data.description,
        "proof_url": None # Assuming default if not provided
    }
    # Simulate the first query returning the accomplishment node
    tx.return_value = {"a": mock_accomplishment_node_data}

    result_node = graph_crud.create_accomplishment(tx, user_email, accomplishment_data)

    assert len(tx.queries) == 2 # One for creating accomplishment, one for linking quest

    # Check first query (create accomplishment)
    assert "CREATE (a:Accomplishment {" in tx.queries[0]
    assert tx.parameters[0]['name'] == accomplishment_data.name

    # Check second query (link to quest)
    assert "MATCH (a:Accomplishment {id: $accomplishment_id})" in tx.queries[1]
    assert "MATCH (q:Quest {id: $quest_id})" in tx.queries[1]
    assert "CREATE (a)-[:FULFILLS]->(q)" in tx.queries[1]
    assert tx.parameters[1]['accomplishment_id'] is not None # Should use the generated ID
    assert tx.parameters[1]['quest_id'] == str(quest_id)

    assert result_node is not None
    assert result_node["name"] == accomplishment_data.name


# --- VC Receipt Test ---
def test_store_vc_receipt():
    tx = MockTransaction()
    accomplishment_id = uuid.uuid4()
    vc_receipt = {
        "id": f"urn:uuid:{uuid.uuid4()}",
        "issuanceDate": "2023-10-27T10:00:00Z"
    }

    # store_vc_receipt doesn't have a meaningful return for the test other than ensuring no error
    # and the query runs with correct parameters.
    # tx.run() itself doesn't return the node, but a result object.
    # If the query was `RETURN r`, we'd mock a return value for `r`.
    # Since it's just SET, we don't need to mock a specific return_value for the query's output.
    # tx.return_value = None # or some mock relationship if we were testing the RETURN r part

    graph_crud.store_vc_receipt(tx, str(accomplishment_id), vc_receipt)

    assert len(tx.queries) == 1
    query = tx.queries[0]
    params = tx.parameters[0]

    assert "MATCH (u:User)-[r:COMPLETED]->(a:Accomplishment {id: $accomplishment_id})" in query
    assert "SET r.vc_id = $vc_id" in query
    assert "r.vc_issuanceDate = $vc_issuanceDate" in query
    assert params['accomplishment_id'] == str(accomplishment_id)
    assert params['vc_id'] == vc_receipt["id"]
    assert params['vc_issuanceDate'] == vc_receipt["issuanceDate"]

# Example of how you might need to adjust if a function is expected to return something from the run
def test_create_quest_returns_node_data():
    tx = MockTransaction()
    quest_data = {"name": "Return Test", "description": "Testing return."}

    # This is what the Neo4j driver's record would look like if 'q' is a node
    # The actual structure might be a neo4j.graph.Node object in reality
    expected_return_data = {
        "id": "some-generated-uuid", # The function generates this
        "name": quest_data["name"],
        "description": quest_data["description"]
    }
    # Set the return_value for the tx.run().single()['q'] call
    tx.return_value = {"q": expected_return_data}

    result = graph_crud.create_quest(tx, quest_data)

    assert result is not None
    assert result["name"] == quest_data["name"]
    assert result["description"] == quest_data["description"]
    assert "id" in result
    assert tx.parameters[0]['id'] is not None # Check that the function generated an ID to pass to the query
    assert tx.parameters[0]['name'] == quest_data["name"]

def test_create_accomplishment_pass_dict_exclude():
    tx = MockTransaction()
    user_email = "test_exclude@example.com"
    quest_id = uuid.uuid4()
    accomplishment_data_model = AccomplishmentCreate(
        name="Test Accomplishment Exclude",
        description="Testing exclusion of fields.",
        proof_url="http://example.com/proof_exclude",
        quest_id=quest_id
    )

    # Data that should be passed to the SET a = $props part of a query if it were structured that way
    # or used individually as $name, $description etc.
    # The current create_accomplishment directly uses fields for the CREATE line.
    expected_props_for_query = {
        "name": accomplishment_data_model.name,
        "description": accomplishment_data_model.description,
        "proof_url": accomplishment_data_model.proof_url
        # id and timestamp are handled by the query itself (randomUUID(), datetime())
    }

    mock_accomplishment_node_data = {
        "id": str(uuid.uuid4()), # Query generates its own ID
        **expected_props_for_query
    }
    tx.return_value = {"a": mock_accomplishment_node_data}


    graph_crud.create_accomplishment(tx, user_email, accomplishment_data_model)

    # The first query is for creating the accomplishment
    params_create = tx.parameters[0]
    assert params_create['user_email'] == user_email
    assert params_create['name'] == accomplishment_data_model.name
    assert params_create['description'] == accomplishment_data_model.description
    assert params_create['proof_url'] == accomplishment_data_model.proof_url
    assert 'id' in params_create # The ID passed to the query for creation

    # Ensure quest_id was not part of the properties set on Accomplishment node directly
    # (it's used for the relationship)
    # This is implicitly tested by checking the params for the CREATE query.

    # The second query is for linking the quest
    if accomplishment_data_model.quest_id:
        assert len(tx.queries) == 2
        params_link = tx.parameters[1]
        assert params_link['quest_id'] == str(quest_id)
        assert 'accomplishment_id' in params_link
    else:
        assert len(tx.queries) == 1
