# skillforge-core
The core skills mapping engine for SkillForge

# SkillForge Core API

![SkillForge CI](https://github.com/SkillForgeHQ/skillforge-core/actions/workflows/ci.yml/badge.svg)

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

### Users (PostgreSQL & Authentication)

User registration and authentication are handled via PostgreSQL.

#### Register User
`POST /users/`

Registers a new user in the PostgreSQL database. This is typically the first step for a new user.

**Path Parameters**

None

**Request Body** (`schemas.UserCreate`)
```json
{
  "email": "newuser@example.com",
  "password": "securepassword123",
  "full_name": "New User"
}
```

| Parameter   | Type   | Description             |
|:------------|:-------|:------------------------|
| `email`     | string | The user's email address (unique). |
| `password`  | string | The user's password.      |
| `full_name` | string | The user's full name (optional). |

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

**Successful Response (201 Created)** (`schemas.User`)
```json
{
  "id": 1,
  "email": "newuser@example.com",
  "full_name": "New User",
  "is_active": true
}
```

**Error Response (400 Bad Request)**
```json
{
  "detail": "Email already registered"
}
```

**Error Response (422 Validation Error)** For invalid request body.

#### Get Current User Details
`GET /users/me`

Fetches the details of the currently authenticated user (based on the Bearer token provided after login). This uses the `get_current_user` dependency which validates the token.

**Path Parameters**

None

**Query Parameters**

None

**Authentication**

Required: Bearer Token in `Authorization` header.

**cURL Example** (Replace `YOUR_ACCESS_TOKEN` with a valid token)
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/users/me' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN'
```

**Successful Response (200 OK)** (`schemas.User`)
```json
{
  "id": 1,
  "email": "test@example.com",
  "full_name": "Test User",
  "is_active": true
}
```

**Error Response (401 Unauthorized)**
```json
{
  "detail": "Could not validate credentials"
}
```

### User Interactions with Skills (Neo4j)

These endpoints manage how users interact with skills in the Neo4j graph database. All are prefixed with `/users`.

#### Create User Node in Graph
`POST /users/graph/users/{email}`

Creates a new `:User` node in the Neo4j graph database. This is separate from PostgreSQL user registration and should typically be called after a user is registered in PostgreSQL if graph features are to be used.

**Path Parameters**

| Parameter | Type   | Description                                           |
|:----------|:-------|:------------------------------------------------------|
| `email`   | string | The email address, serving as the unique ID of the user in the graph. |

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

**Error Response (4xx)** If the user already exists or other graph errors occur.

#### Add Skill to User (Link User to Skill)
`POST /users/graph/users/{email}/skills/{skill_name}`

Links a user to a skill they have acquired by creating a `[:HAS_SKILL]` relationship in the Neo4j graph (e.g., `(:User {email: $email})-[:HAS_SKILL]->(:Skill {name: $skill_name})`).

**Path Parameters**

| Parameter    | Type   | Description                        |
|:-------------|:-------|:-----------------------------------|
| `email`      | string | The unique ID (email) of the user. |
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

**Error Response (404 Not Found)** If the user or skill does not exist in the graph (actual behavior might depend on `graph_crud.add_user_skill` implementation if it checks existence).

#### Get Personalized Learning Path for User
`GET /users/graph/users/{email}/learning-path/{skill_name}`

Generates an ordered, consolidated learning path for a specific user towards a target skill. It considers the skills the user already possesses (via `[:HAS_SKILL]` relationships) and excludes them from the path.

**Path Parameters**

| Parameter    | Type   | Description                                     |
|:-------------|:-------|:------------------------------------------------|
| `email`      | string | The unique ID (email) of the user.              |
| `skill_name` | string | The unique name of the target skill to learn.   |

**Query Parameters**

None

**cURL Example**
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/users/graph/users/test%40example.com/learning-path/Advanced%20Python' \
  -H 'accept: application/json'
```

**Successful Response (200 OK)** (Returns `List[str]`)
```json
[
  "Python Basics",
  "Object-Oriented Programming in Python"
]
```
(Example: If "Advanced Python" depends on "Object-Oriented Programming in Python" and "Python Basics", and the user `test@example.com` already has "Python Basics", this path is returned. If the user had no relevant skills, the full path to "Advanced Python" would be listed.)

**Error Response (404 Not Found)** If the user or target skill does not exist, or if no learning path is found.
```json
{
  "detail": "No learning path found for skill 'TargetSkill'."
}
```

#### Remove Skill From User
`DELETE /users/graph/users/{email}/skills/{skill_name}`

Removes a `[:HAS_SKILL]` relationship between a user and a skill in the Neo4j graph.

**Path Parameters**

| Parameter    | Type   | Description                        |
|:-------------|:-------|:-----------------------------------|
| `email`      | string | The unique ID (email) of the user. |
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

**Error Response (404 Not Found)** If the user or skill (or the relationship) does not exist (actual behavior depends on `graph_crud.remove_user_skill`).

### Skills Management (Neo4j)

These endpoints are for managing Skill nodes and their relationships (dependencies) directly in the Neo4j graph database. All endpoints here are prefixed with `/skills`.

#### Create Skill
`POST /skills/`

Creates a new `:Skill` node in the Neo4j graph database.

**Path Parameters**

None

**Request Body** (`GraphSkillCreate`)
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
  'http://127.0.0.1:8000/skills/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "name": "Data Analysis with Pandas"
}'
```

**Successful Response (201 Created)**
```json
{
  "message": "Skill created in graph",
  "skill": "Data Analysis with Pandas"
}
```

**Error Response (409 Conflict)** If a skill with the same name already exists.
```json
{
  "detail": "Skill already exists in the graph"
}
```

#### List All Skills
`GET /skills/`

Retrieves a list of all skill names from the Neo4j graph database.

**Path Parameters**

None

**Query Parameters**

None

**cURL Example**
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/skills/' \
  -H 'accept: application/json'
```

**Successful Response (200 OK)** (Returns `List[str]`)
```json
[
  "Data Analysis with Pandas",
  "Advanced Data Analysis",
  "Python Basics"
]
```

#### Get Skill by Name
`GET /skills/{skill_name}`

Retrieves a single skill by its name from the Neo4j graph database.

**Path Parameters**

| Parameter  | Type   | Description             |
|:-----------|:-------|:------------------------|
| `skill_name`| string | The name of the skill.  |

**cURL Example**
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/skills/Data%20Analysis%20with%20Pandas' \
  -H 'accept: application/json'
```

**Successful Response (200 OK)** (Returns `str` - the skill name)
```json
"Data Analysis with Pandas"
```

**Error Response (404 Not Found)** If the skill is not found in the graph.
```json
{
  "detail": "Skill not found in graph"
}
```

#### Update Skill Name
`PUT /skills/{skill_name}`

Updates the name of an existing skill in the Neo4j graph database.

**Path Parameters**

| Parameter  | Type   | Description                   |
|:-----------|:-------|:------------------------------|
| `skill_name`| string | The current name of the skill. |

**Request Body** (`SkillUpdate`)
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
  'http://127.0.0.1:8000/skills/Old%20Skill%20Name' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "new_name": "Updated Skill Name"
}'
```

**Successful Response (200 OK)** (Returns `str` - the new skill name)
```json
"Updated Skill Name"
```

**Error Response (404 Not Found)** If the skill `skill_name` is not found.
```json
{
  "detail": "Skill 'Old Skill Name' not found"
}
```
**Error Response (409 Conflict)** If a skill with `new_name` already exists (based on `graph_crud.update_skill` logic, which should prevent this).

#### Delete Skill
`DELETE /skills/{skill_name}`

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
  'http://127.0.0.1:8000/skills/Skill%20To%20Delete' \
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

#### Create Skill Dependency
`POST /skills/{parent_skill}/dependency/{child_skill}`

Creates a `[:DEPENDS_ON]` relationship from a `parent_skill` to a `child_skill` in the Neo4j graph. This signifies that the `child_skill` is a prerequisite for the `parent_skill`.

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
  'http://127.0.0.1:8000/skills/Advanced%20Data%20Analysis/dependency/Data%20Analysis%20with%20Pandas' \
  -H 'accept: application/json' \
  -d ''
```

**Successful Response (201 Created)**
```json
{
  "message": "Dependency from Advanced Data Analysis to Data Analysis with Pandas created."
}
```

**Error Response (404 Not Found)** If either the parent or child skill does not exist (actual behavior depends on `graph_crud.add_skill_dependency`).

#### Get Skill Dependencies (Direct Prerequisites)
`GET /skills/{skill_name}/dependencies`

Retrieves all skills that the specified skill directly depends on (i.e., its direct prerequisites).

**Path Parameters**

| Parameter  | Type   | Description                       |
|:-----------|:-------|:----------------------------------|
| `skill_name`| string | The name of the skill.            |

**Query Parameters**

None

**cURL Example**
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/skills/Advanced%20Data%20Analysis/dependencies' \
  -H 'accept: application/json'
```

**Successful Response (200 OK)** (Returns `List[str]`)
```json
[
  "Data Analysis with Pandas",
  "Statistics Basics"
]
```

**Error Response (404 Not Found)** If the specified skill `skill_name` does not exist.

#### Get Consolidated Skill Learning Path (Generic)
`GET /skills/{skill_name}/path`

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
  'http://127.0.0.1:8000/skills/Advanced%20Data%20Analysis/path' \
  -H 'accept: application/json'
```

**Successful Response (200 OK)** (Returns `List[str]`)
```json
[
  "Python Basics",
  "Data Structures in Python",
  "Statistics Basics",
  "Data Analysis with Pandas"
]
```

**Error Response (404 Not Found)** If no learning path is found for the skill.
```json
{
  "detail": "No learning path found for skill 'TargetSkill'. It may be a foundational skill or does not exist."
}
```

#### Test Neo4j Connection
`GET /skills/test`

A test endpoint to verify the connection to Neo4j and fetch all skill names directly via a Cypher query.

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
