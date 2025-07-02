# skillforge-core
The core skills mapping engine for SkillForge

Role Playing Games, like Skyrim, are really fun to play.  This is somewhat funny, because a great deal of 
what a player does in an RPG is known as "grinding".  Grinding is the process of completing boring tasks
over and over again in order to "level up".  If most of what a player does in an RPG is "grind", why is it fun at all?
"Leveling up" in an RPG is a lot more like work than play.

The answer, I believe, is clarity.  The path to leveling up is absolutely clear.  There's no ambiguity.
Go here, complete this quest, and you will earn exactly this many experience points, gold, and treasure.  If you want
a powerful skill, spell, or ability, the path to obtaining that prize is laid out clearly, including the immediate next step.

Why don't more people learn to play the piano?  Or learn a simple set of new skills, which would unlock better jobs
and higher earning potential?  The answer, I believe, is lack of clarity.  The goal of SkillForge is to provide that clarity, 
no matter what your goal may be.

**SkillForge Vision:**

*   **Skill Tree:** A comprehensive map of all human skills and their unique mastery levels and requirements.
*   **Mentor:** An AI guide who gets to know you and your skills and compentencies through natural conversation.
*   **Quest Engine:** A customized, sequential series of quests, driven by Mentor, designed to help you develop
    your skills and achieve your goals as quickly and efficiently as possible
*   **Guilds:** Groups of people working towards "leveling up" for a given trade or profession
*   **Guild Jobs:** Real, paying work given to Guild Members once they have reached the appropriate level of proficiency

**SkillForge Core**

The mapping engine, which leverages a graph database to model skills and their interdependencies.
The core of our model consists of:

*   `:Skill` nodes: Representing individual skills (e.g., 'JavaScript ES6', 'React Hooks').
*   `:User` nodes: Representing learners in the system.
*   `[:DEPENDS_ON]` relationships: A `(:Skill)-[:DEPENDS_ON]->(:Skill)` relationship indicates a prerequisite.
*   `[:HAS_SKILL]` relationships: A `(:User)-[:HAS_SKILL]->(:Skill)` relationship shows that a user has acquired a particular skill.

**Personalized Learning Paths:**

The primary feature of this API is the ability to generate personalized learning paths. By providing a user's profile,
the system can determine the most efficient sequence of skills to learn next,
filtering out any skills the user has already mastered.

## API Endpoints

This section details the available API endpoints.

### Authentication

#### Get Access Token
`POST /token`

Logs in a user and returns an access token. This endpoint expects standard OAuth2 form data (`username` and `password`). The `username` corresponds to the user's email address.

**Path Parameters**

None

**Request Body (Form Data)**

| Parameter  | Type   | Description                        |
|:-----------|:-------|:-----------------------------------|
| `username` | string | The user's email address.          |
| `password` | string | The user's password.               |

**cURL Example**

```bash
curl -X POST "http://127.0.0.1:8000/token" -H "Content-Type: application/x-www-form-urlencoded" -d "username=test%40example.com&password=yourpassword"
```

**Successful Response (200 OK)**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Error Response (401 Unauthorized)** If the email or password is incorrect.
```json
{
  "detail": "Incorrect email or password"
}
```

**Error Response (422 Validation Error)** If form data is missing or invalid.
```json
{
  "detail": [
    {
      "loc": [
        "body",
        "username"
      ],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Users (PostgreSQL)

#### Register User
`POST /users/`

Registers a new user in the PostgreSQL database.

**Path Parameters**

None

**Request Body**
```json
{
  "email": "newuser@example.com",
  "password": "securepassword123",
  "full_name": "New User"
}
```

| Parameter   | Type   | Description             |
|:------------|:-------|:------------------------|
| `email`     | string | The user's email address. |
| `password`  | string | The user's password.      |
| `full_name` | string | The user's full name.     |

**cURL Example**
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/users/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "email": "newuser@example.com",
  "password": "securepassword123",
  "full_name": "New User"
}'
```

**Successful Response (201 Created)**
```json
{
  "id": 1,
  "email": "newuser@example.com",
  "full_name": "New User",
  "is_active": true
}
```

**Error Response (400 Bad Request)** If the email is already registered.
```json
{
  "detail": "Email already registered"
}
```

**Error Response (422 Validation Error)** If the request body is invalid (e.g., missing fields, invalid email format).
```json
{
  "detail": [
    {
      "loc": [
        "body",
        "password"
      ],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

#### Get Current User
`GET /users/me`

Fetches the details of the currently authenticated user (based on the provided Bearer token).

**Path Parameters**

None

**Query Parameters**

None

**cURL Example** (Replace `YOUR_ACCESS_TOKEN` with a valid token obtained from `/token`)
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/users/me' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN'
```

**Successful Response (200 OK)**
```json
{
  "id": 1,
  "email": "test@example.com",
  "full_name": "Test User",
  "is_active": true
}
```

**Error Response (401 Unauthorized)** If the token is missing, invalid, or expired.
```json
{
  "detail": "Not authenticated"
}
```
```json
{
  "detail": "Could not validate credentials"
}
```

### Users (Neo4j)

#### Create Graph User
`POST /users/graph/users/{email}`

Creates a new User node in the Neo4j graph database.

**Path Parameters**

| Parameter | Type   | Description                                           |
|:----------|:-------|:------------------------------------------------------|
| `email`   | string | The email address, serving as the unique ID of the user. |

**Request Body**

None

**cURL Example**
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/users/graph/users/test%40example.com' \
  -H 'accept: application/json' \
  -d ''
```

**Successful Response (201 Created)**
```json
{
  "message": "User created in graph",
  "email": "test@example.com"
}
```

**Error Response (409 Conflict)** If the user already exists in the graph.
```json
{
  "detail": "User with email 'test@example.com' already exists in graph."
}
```

**Error Response (422 Validation Error)** If the email format is invalid.
```json
{
  "detail": [
    {
      "loc": [
        "path",
        "email"
      ],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

#### Add Skill to User
`POST /users/graph/users/{email}/skills/{skill_name}`

Links a user to a skill they have acquired by creating a `[:HAS_SKILL]` relationship in the Neo4j graph.

**Path Parameters**

| Parameter    | Type   | Description                        |
|:-------------|:-------|:-----------------------------------|
| `email`      | string | The unique ID of the user.         |
| `skill_name` | string | The unique name of the skill.      |

**Request Body**

None

**cURL Example**
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/users/graph/users/test%40example.com/skills/Python' \
  -H 'accept: application/json' \
  -d ''
```

**Successful Response (201 Created)**
```json
{
  "message": "User 'test@example.com' now has skill 'Python'"
}
```

**Error Response (404 Not Found)** If the user or skill does not exist in the graph.
```json
{
  "detail": "User 'nonexistent@example.com' not found in graph."
}
```
```json
{
  "detail": "Skill 'NonExistentSkill' not found in graph."
}
```

**Error Response (422 Validation Error)** If path parameters are invalid.
```json
{
  "detail": [
    {
      "loc": [
        "path",
        "email"
      ],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

#### Get Personalized Learning Path
`GET /users/graph/users/{email}/learning-path/{skill_name}`

Generates an ordered, consolidated learning path for a specific user towards a target skill. It traverses the skill graph to find all prerequisites and then filters out skills the user already possesses (based on `[:HAS_SKILL]` relationships).

**Path Parameters**

| Parameter    | Type   | Description                                     |
|:-------------|:-------|:------------------------------------------------|
| `email`      | string | The unique ID of the user.                      |
| `skill_name` | string | The unique name of the target skill to learn. |

**Query Parameters**

None

**cURL Example**
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/users/graph/users/test%40example.com/learning-path/Advanced%20Python' \
  -H 'accept: application/json'
```

**Successful Response (200 OK)** Returns a list of skill names in the recommended learning order.
```json
[
  "Python Basics",
  "Object-Oriented Programming in Python"
]
```
(Example: If "Advanced Python" depends on "Object-Oriented Programming in Python", which depends on "Python Basics", and the user already has "Python Basics", this would be the path. If the user had none, all three would be listed. If the user already had "Advanced Python", the path would be empty.)

**Error Response (404 Not Found)** If the user or target skill does not exist, or if no learning path is found (e.g., the target skill is foundational or has no prerequisites defined).
```json
{
  "detail": "User 'nonexistent@example.com' not found in graph."
}
```
```json
{
  "detail": "Skill 'NonExistentTargetSkill' not found in graph."
}
```
```json
{
  "detail": "No learning path found for skill 'TargetSkill'. It may be a foundational skill or does not exist."
}
```

**Error Response (422 Validation Error)** If path parameters are invalid.
```json
{
  "detail": [
    {
      "loc": [
        "path",
        "email"
      ],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

#### Remove Skill From User
`DELETE /users/graph/users/{email}/skills/{skill_name}`

Removes a `[:HAS_SKILL]` relationship between a user and a skill in the Neo4j graph.

**Path Parameters**

| Parameter    | Type   | Description                        |
|:-------------|:-------|:-----------------------------------|
| `email`      | string | The unique ID of the user.         |
| `skill_name` | string | The unique name of the skill.      |

**Request Body**

None

**cURL Example**
```bash
curl -X 'DELETE' \
  'http://127.0.0.1:8000/users/graph/users/test%40example.com/skills/OldSkill' \
  -H 'accept: application/json'
```

**Successful Response (200 OK)**
```json
{
  "message": "Skill 'OldSkill' removed from user 'test@example.com'"
}
```

**Error Response (404 Not Found)** If the user or skill does not exist in the graph, or the relationship doesn't exist. (Note: The current API might return 200 OK even if the relationship didn't exist if the user and skill nodes are present. More robust error handling could check for the relationship itself.)
```json
{
  "detail": "User 'nonexistent@example.com' not found in graph."
}
```
```json
{
  "detail": "Skill 'NonExistentSkill' not found in graph."
}
```

**Error Response (422 Validation Error)** If path parameters are invalid.
```json
{
  "detail": [
    {
      "loc": [
        "path",
        "email"
      ],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

### Skills (PostgreSQL)

#### Create Skill (PostgreSQL)
`POST /skills/`

Creates a new skill in the PostgreSQL database.

**Path Parameters**

None

**Request Body**
```json
{
  "name": "PostgreSQL Basics",
  "description": "Learn the fundamentals of PostgreSQL."
}
```

| Parameter   | Type   | Description (Optional)             |
|:------------|:-------|:-----------------------------------|
| `name`      | string | The name of the skill.             |
| `description`| string | A description of the skill.        |

**cURL Example**
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/skills/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "name": "PostgreSQL Basics",
  "description": "Learn the fundamentals of PostgreSQL."
}'
```

**Successful Response (201 Created)**
```json
{
  "id": 1,
  "name": "PostgreSQL Basics",
  "description": "Learn the fundamentals of PostgreSQL."
}
```

**Error Response (400 Bad Request)** If a skill with the same name already exists.
```json
{
  "detail": "Skill with name 'PostgreSQL Basics' already exists."
}
```

**Error Response (422 Validation Error)** If the request body is invalid.
```json
{
  "detail": [
    {
      "loc": [
        "body",
        "name"
      ],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

#### List Skills (PostgreSQL)
`GET /skills/`

Retrieves a list of skills from the PostgreSQL database, with optional pagination.

**Path Parameters**

None

**Query Parameters**

| Parameter | Type    | Description                               | Default |
|:----------|:--------|:------------------------------------------|:--------|
| `skip`    | integer | Number of records to skip for pagination. | 0       |
| `limit`   | integer | Maximum number of records to return.      | 100     |

**cURL Example**
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/skills/?skip=0&limit=10' \
  -H 'accept: application/json'
```

**Successful Response (200 OK)**
```json
[
  {
    "id": 1,
    "name": "PostgreSQL Basics",
    "description": "Learn the fundamentals of PostgreSQL."
  },
  {
    "id": 2,
    "name": "SQL Joins",
    "description": "Master different types of SQL JOINs."
  }
]
```

**Error Response (422 Validation Error)** If query parameters are of invalid types.
```json
{
  "detail": [
    {
      "loc": [
        "query",
        "skip"
      ],
      "msg": "value is not a valid integer",
      "type": "type_error.integer"
    }
  ]
}
```

#### Get Skill (PostgreSQL)
`GET /skills/{skill_name}`

Retrieves a specific skill by its name from the PostgreSQL database.

**Path Parameters**

| Parameter  | Type   | Description              |
|:-----------|:-------|:-------------------------|
| `skill_name`| string | The name of the skill.   |

**cURL Example**
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/skills/PostgreSQL%20Basics' \
  -H 'accept: application/json'
```

**Successful Response (200 OK)**
```json
{
  "id": 1,
  "name": "PostgreSQL Basics",
  "description": "Learn the fundamentals of PostgreSQL."
}
```

**Error Response (404 Not Found)** If the skill with the given name does not exist.
```json
{
  "detail": "Skill not found"
}
```

**Error Response (422 Validation Error)** If `skill_name` is invalid (e.g., empty).
```json
{
  "detail": [
    {
      "loc": [
        "path",
        "skill_name"
      ],
      "msg": "ensure this value has at least 1 characters",
      "type": "value_error.any_str.min_length",
      "ctx": {
        "limit_value": 1
      }
    }
  ]
}
```

#### Update Skill (PostgreSQL)
`PUT /skills/{skill_name}`

Updates the details of an existing skill in the PostgreSQL database.

**Path Parameters**

| Parameter  | Type   | Description                     |
|:-----------|:-------|:--------------------------------|
| `skill_name`| string | The name of the skill to update. |

**Request Body**
```json
{
  "name": "Advanced PostgreSQL",
  "description": "Deep dive into advanced PostgreSQL features."
}
```

| Parameter   | Type   | Description (Optional)             |
|:------------|:-------|:-----------------------------------|
| `name`      | string | The new name for the skill.        |
| `description`| string | The new description for the skill. |

**cURL Example**
```bash
curl -X 'PUT' \
  'http://127.0.0.1:8000/skills/PostgreSQL%20Basics' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "name": "Advanced PostgreSQL",
  "description": "Deep dive into advanced PostgreSQL features."
}'
```

**Successful Response (200 OK)**
```json
{
  "id": 1,
  "name": "Advanced PostgreSQL",
  "description": "Deep dive into advanced PostgreSQL features."
}
```

**Error Response (404 Not Found)** If the skill to update is not found.
```json
{
  "detail": "Skill not found"
}
```

**Error Response (400 Bad Request)** If the new name in the request body already exists for another skill.
```json
{
  "detail": "Skill with name 'Some Other Skill' already exists."
}
```

**Error Response (422 Validation Error)** If path parameters or request body is invalid.
```json
{
  "detail": [
    {
      "loc": [
        "body",
        "name"
      ],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Skills (Neo4j)

#### Create Graph Skill
`POST /skills/graph/skills`

Creates a new Skill node in the Neo4j graph database.

**Path Parameters**

None

**Request Body**
```json
{
  "name": "New Skill Name"
}
```

| Parameter | Type   | Description             |
|:----------|:-------|:------------------------|
| `name`    | string | The name of the skill.  |

**cURL Example**
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/skills/graph/skills' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "name": "Data Analysis with Pandas"
}'
```

**Successful Response (201 Created)** (Note: The API code returns 201, but the example in the original README showed 200. Standard practice is 201 for resource creation.)
```json
{
  "message": "Skill created in graph",
  "skill": "Data Analysis with Pandas"
}
```

**Error Response (409 Conflict)** If a skill with the same name already exists.
```json
{
  "detail": "Skill 'Data Analysis with Pandas' already exists in the graph"
}
```

**Error Response (422 Validation Error)** If the request body is invalid.
```json
{
  "detail": [
    {
      "loc": [
        "body",
        "name"
      ],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

#### List Graph Skills
`GET /skills/graph/skills`

Retrieves a list of all skill names from the Neo4j graph database.

**Path Parameters**

None

**Query Parameters**

None

**cURL Example**
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/skills/graph/skills' \
  -H 'accept: application/json'
```

**Successful Response (200 OK)** Returns a list of skill names.
```json
[
  "Data Analysis with Pandas",
  "Advanced Data Analysis",
  "Python Basics"
]
```

#### Get Graph Skill
`GET /skills/graph/skills/{skill_name}`

Retrieves a single skill by its name from the Neo4j graph database.

**Path Parameters**

| Parameter  | Type   | Description             |
|:-----------|:-------|:------------------------|
| `skill_name`| string | The name of the skill.  |

**cURL Example**
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/skills/graph/skills/Data%20Analysis%20with%20Pandas' \
  -H 'accept: application/json'
```

**Successful Response (200 OK)** Returns the skill name if found.
```json
"Data Analysis with Pandas"
```

**Error Response (404 Not Found)** If the skill is not found in the graph.
```json
{
  "detail": "Skill not found in graph"
}
```

**Error Response (422 Validation Error)** If `skill_name` is invalid.
```json
{
  "detail": [
    {
      "loc": [
        "path",
        "skill_name"
      ],
      "msg": "ensure this value has at least 1 characters",
      "type": "value_error.any_str.min_length",
      "ctx": {
        "limit_value": 1
      }
    }
  ]
}
```

#### Update Graph Skill
`PUT /skills/graph/skills/{skill_name}`

Updates the name of an existing skill in the Neo4j graph database.

**Path Parameters**

| Parameter  | Type   | Description                   |
|:-----------|:-------|:------------------------------|
| `skill_name`| string | The current name of the skill. |

**Request Body**
```json
{
  "new_name": "Updated Skill Name"
}
```

| Parameter | Type   | Description                |
|:----------|:-------|:---------------------------|
| `new_name`| string | The new name for the skill.|

**cURL Example**
```bash
curl -X 'PUT' \
  'http://127.0.0.1:8000/skills/graph/skills/Old%20Skill%20Name' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "new_name": "Updated Skill Name"
}'
```

**Successful Response (200 OK)** Returns the new skill name.
```json
"Updated Skill Name"
```

**Error Response (404 Not Found)** If the skill `skill_name` is not found.
```json
{
  "detail": "Skill 'Old Skill Name' not found"
}
```

**Error Response (409 Conflict)** If a skill with `new_name` already exists.
```json
{
  "detail": "Skill with name 'Updated Skill Name' already exists."
}
```

**Error Response (422 Validation Error)** If path parameters or request body is invalid.
```json
{
  "detail": [
    {
      "loc": [
        "body",
        "new_name"
      ],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

#### Delete Graph Skill
`DELETE /skills/graph/skills/{skill_name}`

Deletes a skill node and its relationships from the Neo4j graph database.

**Path Parameters**

| Parameter  | Type   | Description                        |
|:-----------|:-------|:-----------------------------------|
| `skill_name`| string | The name of the skill to delete.   |

**Request Body**

None

**cURL Example**
```bash
curl -X 'DELETE' \
  'http://127.0.0.1:8000/skills/graph/skills/Skill%20To%20Delete' \
  -H 'accept: application/json'
```

**Successful Response (200 OK)**
```json
{
  "message": "Skill 'Skill To Delete' deleted successfully"
}
```

**Error Response (404 Not Found)** If the skill to delete is not found.
```json
{
  "detail": "Skill not found in graph"
}
```

**Error Response (422 Validation Error)** If `skill_name` is invalid.
```json
{
  "detail": [
    {
      "loc": [
        "path",
        "skill_name"
      ],
      "msg": "ensure this value has at least 1 characters",
      "type": "value_error.any_str.min_length",
      "ctx": {
        "limit_value": 1
      }
    }
  ]
}
```

#### Create Skill Dependency
`POST /skills/graph/skills/{parent_skill}/dependency/{child_skill}`

Creates a `[:DEPENDS_ON]` relationship from a parent skill to a child skill in the Neo4j graph, signifying that the child skill is a prerequisite for the parent skill.

**Path Parameters**

| Parameter     | Type   | Description                                      |
|:--------------|:-------|:-------------------------------------------------|
| `parent_skill`| string | The name of the skill that has the prerequisite. |
| `child_skill` | string | The name of the skill that is the prerequisite.  |

**Request Body**

None

**cURL Example**
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/skills/graph/skills/Advanced%20Data%20Analysis/dependency/Data%20Analysis%20with%20Pandas' \
  -H 'accept: application/json' \
  -d ''
```

**Successful Response (201 Created)** (Note: The API code returns 201, which is appropriate. The original README example showed 200.)
```json
{
  "message": "Dependency from Advanced Data Analysis to Data Analysis with Pandas created."
}
```

**Error Response (404 Not Found)** If either the parent or child skill does not exist in the graph.
```json
{
  "detail": "Parent skill 'NonExistentParentSkill' not found."
}
```
```json
{
  "detail": "Child skill 'NonExistentChildSkill' not found."
}
```

**Error Response (409 Conflict)** If the dependency already exists.
```json
{
  "detail": "Dependency from 'ParentSkill' to 'ChildSkill' already exists."
}
```

**Error Response (422 Validation Error)** If path parameters are invalid.
```json
{
  "detail": [
    {
      "loc": [
        "path",
        "parent_skill"
      ],
      "msg": "ensure this value has at least 1 characters",
      "type": "value_error.any_str.min_length",
      "ctx": {
        "limit_value": 1
      }
    }
  ]
}
```

#### Get Skill Dependencies (Direct Prerequisites)
`GET /skills/graph/skills/{skill_name}/dependencies`

Retrieves all skills that the specified skill directly depends on (i.e., its direct prerequisites or children in the dependency tree).

**Path Parameters**

| Parameter  | Type   | Description                       |
|:-----------|:-------|:----------------------------------|
| `skill_name`| string | The name of the parent skill.     |

**Query Parameters**

None

**cURL Example**
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/skills/graph/skills/Advanced%20Data%20Analysis/dependencies' \
  -H 'accept: application/json'
```

**Successful Response (200 OK)** Returns a list of skill names that are direct prerequisites.
```json
[
  "Data Analysis with Pandas",
  "Statistics Basics"
]
```
(Example: If "Advanced Data Analysis" directly depends on "Data Analysis with Pandas" and "Statistics Basics".)

**Error Response (404 Not Found)** If the specified skill `skill_name` does not exist.
```json
{
  "detail": "Skill 'NonExistentSkill' not found."
}
```

**Error Response (422 Validation Error)** If `skill_name` is invalid.
```json
{
  "detail": [
    {
      "loc": [
        "path",
        "skill_name"
      ],
      "msg": "ensure this value has at least 1 characters",
      "type": "value_error.any_str.min_length",
      "ctx": {
        "limit_value": 1
      }
    }
  ]
}
```

#### Get Consolidated Skill Learning Path (Not User-Specific)
`GET /skills/graph/skills/{skill_name}/path`

Finds a single, consolidated learning path for a target skill from the Neo4j graph. This path lists all prerequisite skills in a recommended learning order, irrespective of any specific user.

**Path Parameters**

| Parameter  | Type   | Description                                    |
|:-----------|:-------|:-----------------------------------------------|
| `skill_name`| string | The name of the target skill to get the path for. |

**Query Parameters**

None

**cURL Example**
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/skills/graph/skills/Advanced%20Data%20Analysis/path' \
  -H 'accept: application/json'
```

**Successful Response (200 OK)** Returns a list of skill names in the recommended learning order.
```json
[
  "Python Basics",
  "Data Structures in Python",
  "Statistics Basics",
  "Data Analysis with Pandas"
]
```
(Example: If "Advanced Data Analysis" has the above skills as its complete prerequisite chain.)

**Error Response (404 Not Found)** If no learning path is found for the skill (e.g., it's a foundational skill with no prerequisites or does not exist).
```json
{
  "detail": "No learning path found for skill 'TargetSkill'. It may be a foundational skill or does not exist."
}
```

**Error Response (422 Validation Error)** If `skill_name` is invalid.
```json
{
  "detail": [
    {
      "loc": [
        "path",
        "skill_name"
      ],
      "msg": "ensure this value has at least 1 characters",
      "type": "value_error.any_str.min_length",
      "ctx": {
        "limit_value": 1
      }
    }
  ]
}
```

#### Test Neo4j Connection and Fetch Skill Titles
`GET /skills/graph/test`

A test endpoint to verify the connection to Neo4j and fetch all skill names directly via a Cypher query. Useful for debugging.

**Path Parameters**

None

**Query Parameters**

None

**cURL Example**
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/skills/graph/test' \
  -H 'accept: application/json'
```

**Successful Response (200 OK)** Returns a list of all skill names present in the graph.
```json
[
  "Skill A",
  "Skill B",
  "Skill C"
]
```
