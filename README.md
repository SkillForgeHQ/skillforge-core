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

Create User: POST /api/users

**Path Parameters**

| Parameter | Type   | Description                |
| :-------- | :----- | :------------------------- |
| `userId`  | string | The unique ID of the user. |

**Query Parameters**

| Parameter | Type   | Description                                  | Required |
| :-------- | :----- | :------------------------------------------- | :------- |
| `target`  | string | The `name` of the final skill to be learned. | Yes      |

cURL Example:

curl -X GET "http://localhost:8080/api/users/12345/learning-path?target=React%20Testing%20Library"

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

Add Skill to User: POST /api/users/{userId}/skills

Create Skill: POST /api/skills

Define Skill Dependency: POST /api/skills/dependencies (or however you structured it)

**Get Personalized Learning Path**
GET /api/users/{userId}/learning-path

This endpoint generates an ordered, consolidated learning path for a specific user, starting from a target skill. 
It traverses the skill graph to find all prerequisites, 
then filters out skills the user already possesses based on their [:HAS_SKILL] relationships.

**Path Parameters**

| Parameter | Type   | Description                |
| :-------- | :----- | :------------------------- |
| `userId`  | string | The unique ID of the user. |

**Query Parameters**

| Parameter | Type   | Description                                  | Required |
| :-------- | :----- | :------------------------------------------- | :------- |
| `target`  | string | The `name` of the final skill to be learned. | Yes      |

cURL Example:

curl -X GET "http://localhost:8080/api/users/12345/learning-path?target=React%20Testing%20Library"

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