Project Context for SkillForge AI Development
1. Mission & Vision
Project Name: SkillForge

Vision: To create an AI-driven platform that moves beyond abstract skill labels and builds a user's professional story through a graph of concrete, verifiable accomplishments. SkillForge will map a user's goals to a personalized learning path of "quests," verify the work they've done, and issue portable credentials for their accomplishments.

Founder: Tyler, a solo founder with 18 years of entrepreneurship experience, currently upgrading his software engineering skills to achieve a career goal: a role on an AR/AI team at a company like Meta or Google, or a $1M+ acquihire for SkillForge by mid-2027.

2. The Core Architectural Shift: From "Mastery" to "Accomplishments"
This is the most critical context for the current set of tasks.

The Old Model (Being Deprecated):
We initially modeled skills with abstract, arbitrary levels. A user was linked to a skill via a :Mastery node (e.g., User -> Mastery Level 4 -> Skill: Python).

The Flaw: This model is not representative of real-world learning. "Level 4" is meaningless without context. It's not verifiable, not portable, and provides poor data for generating the next logical step in a user's learning journey.

The New Model (Our Destination):
We are refactoring to an evidence-based model centered on tangible work. The new graph structure is:

(User) -[:COMPLETED]-> (Accomplishment) -[:DEMONSTRATES]-> (Skill)

Why this is superior:

It's Concrete: Instead of "Level 4 Python," a user's profile is built on facts like "Completed: 'Deployed a containerized FastAPI application'."

It's Verifiable: Each :Accomplishment node is based on proof (code, documents, etc.) that can be analyzed and verified by our AI.

It Aligns with Credentials: We can issue a Verifiable Credential (VC) for a specific, proven accomplishment, which is far more credible than a VC for an abstract level.

It Powers Better AI: The graph of accomplishments provides a rich, factual dataset to power our recommendation engine for generating the next "quest."

Your primary mission is to help execute this architectural refactor.

3. Current Tech Stack & Deployment
Backend Framework: FastAPI (Python)

Databases:

Application Data: PostgreSQL

Knowledge Graph: Neo4j

AI/LLM: LangChain with gpt-4o-mini and other models for analysis and generation.

Containerization: The entire stack is containerized with Docker and orchestrated with docker-compose.yml.

Deployment: Deployed on Render, connected to managed cloud databases.

CI/CD: Continuous Integration is handled by GitHub Actions (.github/workflows/ci.yml), which runs pytest on every push to main.

4. Key Code Files & Directories
When given prompts, you will primarily be interacting with the following parts of the codebase located in the api/ directory:

api/main.py: The entry point for the FastAPI application.

api/database.py: Contains database session and connection logic for PostgreSQL and Neo4j.

api/schemas.py: Contains all Pydantic schemas used for API request/response validation and data structure definition. You will be modifying this heavily.

api/graph_crud.py: Contains all the functions that execute Cypher queries to interact with the Neo4j graph. This file is central to the refactor.

api/routers/: This directory contains the API endpoint definitions.

users.py: User-related endpoints.

skills.py: Skill-related endpoints.

goals.py: Endpoints related to parsing goals and processing accomplishments. The logic here will be moved.

accomplishments.py: A new router file you will create to handle the submission and processing of accomplishments under the new model.

5. The Refactoring Plan
We will be executing this change iteratively. The plan is as follows:

Build the Foundation: Introduce the new :Accomplishment nodes and relationships without removing the old model.

Implement the AI Processor: Create the core endpoint that receives user-submitted proof, uses an LLM to verify it and extract skills, and updates the graph with the new model.

Deprecate and Remove: Once the new system is powering user skill tracking and path generation, systematically remove all code related to the old :Mastery model (schemas, CRUD functions, endpoints).

Update Documentation: Ensure the README.md and API documentation accurately reflect the new, superior architecture.