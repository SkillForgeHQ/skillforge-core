Project Context for SkillForge AI Development
1. Mission & Vision
Project Name: SkillForge

Vision: To create an AI-driven platform that builds a user's professional story through a graph of concrete, verifiable accomplishments. SkillForge maps goals to a guided, one-step-at-a-time journey, verifies completed work, and issues portable, cryptographic credentials for each accomplishment.

2. Core Graph Logic & State Machine (Source of Truth)
This section describes the exact, non-negotiable behavior of our graph data. The system follows a "Hub-and-Spoke" model where the :Goal node is the master controller.

Event 1: Goal Creation
Trigger: A user submits a high-level goal to the POST /api/goals/parse endpoint.

Action Sequence:

The AI parser generates a full, ordered list of all sub-tasks required to complete the goal.

A single :Goal node is created. The full, ordered list of sub-tasks is stored as a JSON string in its full_plan_json property. Its status is set to "in-progress".

A [:HAS_GOAL] relationship is created from the :User to the new :Goal.

The system reads only the first task from the full_plan_json.

A single :Quest node is created for this first task.

A [:HAS_ACTIVE_QUEST] relationship is created from the :Goal to this new :Quest.

A [:HAS_QUEST] relationship is created from the :User to this new :Quest.

Result: The user has one active quest. The graph knows the full plan, but only the first step is an actual :Quest node.

Event 2: Quest Completion & Advancement
Trigger: A user submits an accomplishment to the POST /api/accomplishments/process endpoint, linking it to the active quest via quest_id.

Action Sequence:

An :Accomplishment node is created.

A [:COMPLETED] relationship is created from the :User to the new :Accomplishment.

A [:FULFILLS] relationship is created from the :Accomplishment to the :Quest that was just completed.

The system calls the advance_goal logic, which performs the following:
a. It finds the completed :Quest and its parent :Goal.
b. The [:HAS_ACTIVE_QUEST] relationship on the :Goal is deleted. The [:PRECEDES] relationship is created between the old quest and the new one.
c. It reads the full_plan_json from the :Goal and finds the next task in the sequence.

Result (If there is a next quest):

A new :Quest node is created for the next task.

A new [:HAS_ACTIVE_QUEST] relationship is created from the :Goal to the new :Quest.

A new [:HAS_QUEST] relationship is created from the :User to the new :Quest.

Result (If this was the FINAL quest): See Event 3.

Event 3: Goal Completion
Trigger: The advance_goal logic is called for the final quest in the full_plan_json.

Action Sequence:

The status property on the :Goal node is updated from "in-progress" to "completed".

A new [:ACHIEVED_GOAL] relationship is created from the :User to the :Goal.

Result: The user's journey for this goal is complete and recorded in the graph.

3. Technology Stack & Deployment
Backend: FastAPI (Python)

Databases: PostgreSQL, Neo4j

CI/CD: GitHub Actions with service containers.