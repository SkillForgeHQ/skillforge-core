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

Skill Tree: a comprehensive map of all human skills and their unique mastery levels and requirements.
Mentor: an AI guide who gets to know you and your skills and compentencies through natural conversation.
Quest Engine: a customized, sequential series of quests, driven by Mentor, designed to help you develop 
your skills and achieve your goals as quickly and efficiently as possible
Guilds: groups of people working towards "leveling up" for a given trade or profession
Guild Jobs: real, paying work given to Guild Members once they have reached the appropriate level of proficiency

**SkillForge Core**

The mapping engine, which leverages a graph database to model skills and their interdependencies.
The core of our model consists of:

:Skill nodes: Representing individual skills (e.g., 'JavaScript ES6', 'React Hooks').

:User nodes: Representing learners in the system.

[:DEPENDS_ON] relationships: A (:Skill)-[:DEPENDS_ON]->(:Skill) relationship indicates a prerequisite.

[:HAS_SKILL] relationships: A (:User)-[:HAS_SKILL]->(:Skill) relationship shows that a user has acquired a particular skill."

**Personalized Learning Paths:**

The primary feature of this API is the ability to generate personalized learning paths. By providing a user's profile, 
the system can determine the most efficient sequence of skills to learn next, 
filtering out any skills the user has already mastered.

API Endpoints:

Create Graph User: 
POST /users/graph/users/{email}

**Path Parameters**

| Parameter  | Type   | Description                                            |
|:-----------| :----- |:-------------------------------------------------------|
| `email`    | string | The email address serves as the unique ID of the user. |
| `password` | string | The user's password                                    |

**Query Parameters**

None

cURL Example:

curl -X 'POST' \
  'http://127.0.0.1:8000/users/graph/users/test%40tester.com' \
  -H 'accept: application/json' \
  -d ''

Successful Response (201 OK)

{
  "message": "User created in graph",
  "email": "test@tester.com"
}

Error Response (422 Validation Error)

{
  "detail": [
    {
      "loc": [
        "string",
        0
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}

Add Skill to User: 
POST /users/graph/users/{email}/skills/{skill_name}

**Path Parameters**

| Parameter     | Type   | Description                 |
|:--------------| :----- |:----------------------------|
| `email`       | string | The unique ID of the user.  |
| `skill_name`  | string | The unique ID of the skill. |

**Query Parameters**

None

cURL Example:

curl -X 'POST' \
  'http://127.0.0.1:8000/users/graph/users/test%40tester.com/skills/Hold%20Fork' \
  -H 'accept: application/json' \
  -d ''

Successful Response (201 OK)

{
  "message": "User 'test@tester.com' now has skill 'Hold Fork'"
}

Error Response (422 Validation Error)

{
  "detail": [
    {
      "loc": [
        "string",
        0
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}


Create Graph Skill: 
POST /skills/graph/skills

**Path Parameters**

None

**Request Body**

{
  "name": "Light Burner on Gas Stovetop"
}

cURL Example:

curl -X 'POST' \
  'http://127.0.0.1:8000/skills/graph/skills' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "name": "Light Burner on Gas Stovetop"
}'

Successful Response (200 OK)

{
  "message": "Skill created in graph",
  "skill": "Light Burner on Gas Stovetop"
}

Error Response (422 Validation Error)

{
  "detail": [
    {
      "loc": [
        "string",
        0
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}

### **Create Skill Dependency**

`POST /skills/graph/skills/{parent_skill}/dependency/{child_skill}`

Creates a `[:DEPENDS_ON]` relationship from a parent skill to a child skill, signifying that the child is a prerequisite for the parent.

**Path Parameters**

| Parameter      | Type   | Description                                 |
|:---------------|:-------|:--------------------------------------------|
| `parent_skill` | string | The name of the skill that has a prerequisite. |
| `child_skill`  | string | The name of the skill that is the prerequisite. |

**cURL Example**

```bash
curl -X 'POST' \
  '[http://127.0.0.1:8000/skills/graph/skills/React%20Testing%20Library/dependency/Jest](http://127.0.0.1:8000/skills/graph/skills/React%20Testing%20Library/dependency/Jest)' \
  -H 'accept: application/json' \
  -d ''

Successful Response (200 OK)

{
  "message": "Dependency created: Skill 'React Testing Library' now depends on 'Jest'"
}

Error Response (422 Validation Error)

{
  "detail": [
    {
      "loc": [
        "string",
        0
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}

**Get Personalized Learning Path**
GET /users/graph/users/{email}/learning-path/{skill_name}

This endpoint generates an ordered, consolidated learning path for a specific user, starting from a target skill. 
It traverses the skill graph to find all prerequisites, 
then filters out skills the user already possesses based on their [:HAS_SKILL] relationships.

**Path Parameters**

| Parameter    | Type   | Description                 |
|:-------------| :----- |:----------------------------|
| `email`      | string | The unique ID of the user.  |
| `skill_name` | string | The unique ID of the skill. |

cURL Example:

curl -X 'GET' \
  '[http://127.0.0.1:8000/users/graph/users/test%40tester.com/learning-path/React%20Testing%20Library](http://127.0.0.1:8000/users/graph/users/test%40tester.com/learning-path/React%20Testing%20Library)' \
  -H 'accept: application/json'

Successful Response (200 OK)

{
  "path": [
    {
      "name": "JavaScript Fundamentals",
      "description": "Core concepts of the JavaScript language."
    },
    {
      "name": "React Fundamentals",
      "description": "Understanding components, state, and props."
    },
    {
      "name": "Jest",
      "description": "A delightful JavaScript Testing Framework."
    }
  ]
}

Error Response (404 Not Found)

{
  "error": "User with ID 12345 not found."
}